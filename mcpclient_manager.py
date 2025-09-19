import os
import json
import asyncio
import logging
import traceback
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client
from contextlib import asynccontextmanager
from typing import Any, List, Optional

# 設定全域 logger
logger = logging.getLogger("mcpclient_manager_debug")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler("debug.log", encoding='utf-8')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)

def load_config(config_path="config.json"):
    """Load configuration from config file"""
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"default_server_type": "git"}

def get_available_servers(config_path="config.json"):
    """Get list of available MCP servers from config"""
    config = load_config(config_path)
    servers = config.get("MCP_Servers", {})
    return list(servers.keys())

class MCPClientManager:
    """Enhanced MCP client that supports multiple connection types"""
    
    def __init__(self, server_type: str, config_path="config.json"):
        self.server_type = server_type
        self.config_path = config_path
        self.session = None
        self._client = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.session:
                try:
                    await self.session.__aexit__(exc_type, exc_val, exc_tb)
                except (GeneratorExit, RuntimeError, Exception) as e:
                    print(f"[Warning] Exception during session async exit: {e}")
            if self._client:
                try:
                    await self._client.__aexit__(exc_type, exc_val, exc_tb)
                except (GeneratorExit, RuntimeError, Exception) as e:
                    print(f"[Warning] Exception during client async exit: {e}")
        except Exception as e:
            print(f"[Warning] Exception during MCPClientManager __aexit__: {e}")

    async def connect(self):
        """Establishes connection to MCP server"""
        config = load_config(self.config_path)
        server_config = config["MCP_Servers"].get(self.server_type, {})
        mode = server_config.get("mode", "stdio")
        
        if mode == "stdio":
            connection_config = server_config["connection"]
            args = connection_config["args"].copy()
            
            server_params = StdioServerParameters(
                command=connection_config["command"],
                args=args,
                env=connection_config.get("env")
            )
            
            self._client = stdio_client(server_params)
            self.read, self.write = await self._client.__aenter__()
            session = ClientSession(self.read, self.write)
            self.session = await session.__aenter__()
            await self.session.initialize()
            
        elif mode == "sse":
            connection_config = server_config["connection"]
            url = connection_config["url"]
            self._client = sse_client(url)
            self.read, self.write = await self._client.__aenter__()
            session = ClientSession(self.read, self.write)
            self.session = await session.__aenter__()
            await self.session.initialize()
            
        elif mode == "http":
            connection_config = server_config["connection"]
            url = connection_config["url"]
            self._client = streamablehttp_client(url)
            self.read, self.write, _ = await self._client.__aenter__()
            session = ClientSession(self.read, self.write)
            self.session = await session.__aenter__()
            await self.session.initialize()
        else:
            raise ValueError(f"Unsupported connection mode: {mode}")

    async def get_available_tools(self) -> List[Any]:
        """List available tools"""
        if not self.session:
            raise RuntimeError("Not connected to MCP server")
            
        tools = await self.session.list_tools()
        
        # Handle different response formats from different servers
        try:
            if hasattr(tools, 'tools'):
                # Standard MCP response format
                return tools.tools
            elif isinstance(tools, tuple) and len(tools) >= 3:
                # Git server format: (_, _, tools_list)
                return tools[2]
            elif isinstance(tools, list):
                # Direct list format
                return tools
            else:
                print(f"Unexpected tools response format: {type(tools)}")
                return []
        except Exception as e:
            print(f"Error parsing tools response: {e}")
            print(f"Raw tools response: {tools}")
            return []

    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Call a tool with given arguments"""
        if not self.session:
            raise RuntimeError("Not connected to MCP server")
        result = await self.session.call_tool(tool_name, arguments=arguments)
        return result 

def initialize_agent_and_tools(selected_model, selected_server, _):
    import asyncio
    from ollama_toolmanager import OllamaToolManager
    from ollama_agent import OllamaAgent

    async def _init():
        tool_manager = OllamaToolManager()
        agent = OllamaAgent(selected_model, tool_manager, None)
        # MCPClientManager 僅在此 async context 內使用，連線完即釋放
        async with MCPClientManager(selected_server) as mcpclient:
            tools_list = await mcpclient.get_available_tools()
            
            # 註冊時用 wrapper，每次呼叫都新建 context
            async def call_tool_wrapper(tool_name, arguments):
                # Excel 工具參數名稱自動修正，支援多種常見名稱
                if tool_name.startswith("excel_"):
                    for k in ["file_path", "path", "filepath", "file","filePath"]:
                        if k in arguments and "fileAbsolutePath" not in arguments:
                            arguments["fileAbsolutePath"] = arguments.pop(k)
                
                # log 修正後的 arguments
                logger.debug(f"[DEBUG] call_tool_wrapper: tool_name={tool_name}, arguments={json.dumps(arguments, ensure_ascii=False)}")
                print(f"[DEBUG] call_tool_wrapper: tool_name={tool_name}, arguments={arguments}")
                
                try:
                    print(f"[DEBUG] 建立 MCP 連線到 {selected_server}")
                    async with MCPClientManager(selected_server) as client:
                        print(f"[DEBUG] MCP 連線建立成功，開始呼叫工具 {tool_name}")
                        result = await client.call_tool(tool_name, arguments)
                        print(f"[DEBUG] 工具 {tool_name} 執行成功")
                        return result
                        
                except Exception as e:
                    error_msg = f"[ERROR] 工具 {tool_name} 執行失敗: {str(e)}"
                    print(error_msg)
                    logger.error(error_msg)
                    logger.error(f"[ERROR] 詳細錯誤: {traceback.format_exc()}")
                    return {
                        'tool': tool_name,
                        'content': [{
                            'text': f"工具執行失敗: {str(e)}"
                        }],
                        'status': 'error',
                        'error_details': str(e)
                    }
            for tool in tools_list:
                agent.tool_manager.register_tool(
                    name=tool.name,
                    function=call_tool_wrapper,
                    description=tool.description,
                    inputSchema=tool.inputSchema
                )
            return agent
    return asyncio.run(_init()) 