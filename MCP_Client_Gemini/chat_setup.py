import os
import json
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client
from contextlib import asynccontextmanager
from google.genai import types

def load_config(config_path="config.json"):
    """Load configuration from config file"""
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"Chat_UI_Enable": True}

@asynccontextmanager
async def connect_to_server(server_type=None):
    """Connect to MCP server based on configuration"""
    
    config = load_config()
    if server_type is None:
        server_type = config.get("default_server_type", "filesystem")
    server_config = config["MCP_Servers"].get(server_type, {})
    mode = server_config.get("mode", "stdio")
    
    if mode == "stdio":
        # Setup stdio connection
        connection_config = server_config["connection"]
        args = connection_config["args"].copy()
        workspace = server_config.get("workspace")
        if workspace:
            args.append(os.path.abspath(workspace))
        server_params = StdioServerParameters(
            command=connection_config["command"],
            args=args,
            env=connection_config["env"]
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session
    elif mode == "sse":
        connection_config = server_config["connection"]
        url = connection_config["url"]
        async with sse_client(url) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
            # Initialize the connection
                await session.initialize()
                yield session
    elif mode == "http":
        # Setup HTTP connection using streamablehttp_client
        connection_config = server_config["connection"]
        url = connection_config["url"]
        
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session
    else:
        raise ValueError(f"Unsupported connection mode: {mode}")

def clean_schema(schema):
    """Recursively clean schema by removing unsupported fields"""
    if not isinstance(schema, dict):
        return schema
        
    # Create a copy to avoid modifying the original
    cleaned = schema.copy()
    
    # Remove unsupported fields
    cleaned.pop('$schema', None)
    cleaned.pop('additionalProperties', None)
    
    # Recursively clean nested objects
    if 'properties' in cleaned:
        cleaned['properties'] = {
            k: clean_schema(v) for k, v in cleaned['properties'].items()
        }
    
    # Clean items in arrays
    if 'items' in cleaned:
        cleaned['items'] = clean_schema(cleaned['items'])
        
    # Clean any other nested objects
    for key, value in cleaned.items():
        if isinstance(value, dict):
            cleaned[key] = clean_schema(value)
        elif isinstance(value, list):
            cleaned[key] = [clean_schema(item) if isinstance(item, dict) else item for item in value]
            
    return cleaned

def convert_schema_to_gemini_format(schema):
    """Convert JSON schema to Gemini's expected format"""
    if not schema:
        return {"type": "object", "properties": {}}
        
    # Clean the schema recursively
    cleaned_schema = clean_schema(schema)
    
    # Ensure required fields are present
    if 'properties' not in cleaned_schema:
        cleaned_schema['properties'] = {}
    if 'type' not in cleaned_schema:
        cleaned_schema['type'] = 'object'
        
    return cleaned_schema

async def get_mcp_tools(session):
    """Get available tools from the MCP server and convert to Gemini format"""
    try:
        tools = await session.list_tools()
        if not tools or not hasattr(tools, 'tools'):
            return []
            
        # Print available tools for debugging
        print("\nAvailable tools:")
        for i, tool in enumerate(tools.tools):
            print(f"{i+1}. {tool.name}")
        for i, tool in enumerate(tools.tools):
            print(f"{i+1}. {tool.name} inputSchema: {tool.inputSchema}")    
        # Convert to Gemini tool format
        return [
            types.Tool(function_declarations=[{
                "name": tool.name,
                "description": tool.description,
                #"parameters": tool.inputSchema,
                "parameters": convert_schema_to_gemini_format(tool.inputSchema)
            }]) for tool in tools.tools
        ]
    except Exception as e:
        print(f"Error getting tools: {str(e)}")
        return [] 