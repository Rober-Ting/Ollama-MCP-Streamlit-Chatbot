import ollama
from ollama_toolmanager import OllamaToolManager
import json
from ollama._client import ResponseError
import logging

# 設定自訂 logger，只寫本檔案 debug 訊息
logger = logging.getLogger("ollama_agent_debug")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler("debug.log", encoding='utf-8')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.handlers = [handler]

class OllamaAgent:
    def __init__(self,model:str,
                 tool_manager: OllamaToolManager,
                 default_prompt=None) -> None:
        # 從 config.json 讀取 default_prompt
        if default_prompt is None:
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                default_prompt = config.get("model_setting", {}).get("default_prompt", "You are a helpful assistant who can use available tools to solve problems")
            except Exception:
                default_prompt = "You are a helpful assistant who can use available tools to solve problems"
        self.model = model
        self.default_prompt = default_prompt
        self.messages = []
        self.tool_manager = tool_manager

    async def get_response(self, content: str, stream: bool = False):
        """
        回傳完整回應（非 stream）或 streaming generator（stream=True）。
        這裡不做 stream 判斷，全部交給 handle_response 處理。
        """
        self.messages.append({'role': 'user', 'content': content})
        logger.debug(f"[DEBUG] messages: {self.messages}")
        try:
            # 判斷模型是否支援 tool call
            from model_setting import get_model_tool_support
            support_tool = get_model_tool_support(self.model)
            if support_tool:
                tools_schema = self.tool_manager.get_tools()
                logger.debug(f"[DEBUG] tools schema sent to LLM: {json.dumps(tools_schema, ensure_ascii=False)}")
                query = ollama.chat(
                    model=self.model,
                    messages=self.messages,
                    tools=tools_schema,
                )
            else:
                logger.debug(f"[DEBUG] model {self.model} does not support tools")

                query = ollama.chat(
                    model=self.model,
                    messages=self.messages,
                )
            async for chunk in self.handle_response(query, stream=stream):
                yield chunk
        except ResponseError as e:
            if "does not support tools" in str(e):
                from model_setting import set_model_tool_support
                set_model_tool_support(self.model, False)
                yield " "
                return
            else:
                yield f"[Ollama ResponseError: {e}]"
        except Exception as e:
            yield f"[Error in get_response: {e}]"

    async def handle_response(self, response, stream=False):
        try:
            tool_calls = getattr(response.message, 'tool_calls', None)
            logger.debug(f"[DEBUG] response.message.tool_calls: {tool_calls}")
            if tool_calls:
                self.messages.append({
                    'role': 'tool',
                    'content': str(response)
                })
                tool_payload = tool_calls[0]
                result = await self.tool_manager.execute_tool(tool_payload)
                logger.debug(f"[DEBUG] tool result: {result}")
                # 判斷 tool call 是否 error
                if isinstance(result, dict) and result.get("status") == "error":
                    yield {
                        "tool_call": str(tool_payload),
                        "tool_result": f"❌ 工具執行失敗: {result['content'][0]['text']}",
                        "final_response": None
                    }
                    return
                # 正常回傳
                tool_response = []
                logger.debug(f"[DEBUG] Processing tool result: {result}")
                logger.debug(f"[DEBUG] Result type: {type(result)}")
                logger.debug(f"[DEBUG] Result has content attribute: {hasattr(result, 'content')}")
                
                if hasattr(result, 'content') and result.content:
                    logger.debug(f"[DEBUG] Content type: {type(result.content)}")
                    logger.debug(f"[DEBUG] Content length: {len(result.content) if isinstance(result.content, list) else 'N/A'}")
                    
                    for i, content in enumerate(result.content):
                        logger.debug(f"[DEBUG] Processing content item {i}: {type(content)}")
                        if hasattr(content, 'text'):
                            logger.debug(f"[DEBUG] Content text: {content.text[:100]}...")  # 只記錄前100字元
                            tool_response.append(content.text)
                        else:
                            logger.debug(f"[DEBUG] Content as string: {str(content)[:100]}...")
                            tool_response.append(str(content))
                else:
                    logger.debug(f"[DEBUG] No content attribute or empty content, using result as string")
                    tool_response.append(str(result))
                
                final_tool_result = "".join(tool_response)
                logger.debug(f"[DEBUG] Final tool result length: {len(final_tool_result)}")
                
                yield {
                    "tool_call": str(tool_payload),
                    "tool_result": final_tool_result,
                    "final_response": None
                }
                return
            content = getattr(response.message, 'content', None)
            logger.debug(f"[DEBUG] response.message.content: {content}")
            if content:
                if stream:
                    for i in range(1, len(content)+1):
                        yield content[:i]
                else:
                    yield content
                return
            yield "[No valid response from model]"
        except Exception as e:
            print(e)
            logger.error(f"[ERROR] Error in handle_response: {e}")
            yield f"[Error in handle_response: {e}]"
