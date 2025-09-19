import os
import json
import asyncio
from google import genai
from google.genai import types
from chat_setup import connect_to_server, get_mcp_tools, load_config

async def run_async_chat():
    """Run async chat with the selected server configuration"""
    api_key = os.getenv("GOOGLE_API_KEY")
    config = load_config()
    
    # Initialize Gemini model from config
    model_config = config["Model"]
    model_name = model_config["name"]
    client = genai.Client(api_key=api_key)
    # --- 建立聊天會話 (async 版本) ---
    chat = client.aio.chats.create(model=model_name)
    async with connect_to_server() as session:
        # 取得工具
        tools = await get_mcp_tools(session)
        print("Tools retrieved done.")
        
        # 主對話循環
        while True:
            prompt = input("你: ")
            if prompt.lower() in ["quit", "exit"]:
                print("結束對話。")
                break

            # 構建初始請求內容 (stateless 風格)
            #contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]
            #contents = types.Content(role="user", parts=[types.Part(text=prompt)])
            contents = prompt
            # 構建請求配置
            generation_config = types.GenerateContentConfig(
                temperature=model_config["temperature"],
                tools=tools,
                tool_config=types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode=model_config["tool_config"]["function_calling_config"]["mode"]
                    )
                )
            )
            
            # 第一次呼叫 Gemini API
            print("思考中...")
            """
            response = await client.aio.models.generate_content(
                model=model_config["name"],
                contents=contents,
                config=generation_config
            )
            """
            response = await chat.send_message(
                message=contents,
                config=generation_config
            )
            
            # --- 內層循環：處理函數呼叫序列 (類似 RAG_GenAPI) ---
            MAX_FUNCTION_CALL_TURNS = 50
            function_turn = 0
            final_response_text = ""
            
            while function_turn < MAX_FUNCTION_CALL_TURNS:
                # 檢查回應中是否有候選內容
                if not hasattr(response, 'candidates') or not response.candidates:
                    print("回應中沒有候選內容")
                    break
                
                candidate = response.candidates[0]
                if not candidate or not hasattr(candidate, 'content'):
                    print("候選內容無效")
                    break
                
                # 儲存這個模型回應，稍後會加到 contents 中
                model_content = candidate.content
                
                # 檢查是否有函數呼叫
                function_calls = []
                if hasattr(response, "function_calls"):
                    function_calls = response.function_calls
                
                # 如果沒有函數呼叫，那我們得到了最終答案
                if not function_calls:
                    print("\nGemini 未要求執行函數，提取最終回應。")
                    final_parts = model_content.parts if hasattr(model_content, 'parts') else []
                    final_response_text = "".join(
                        part.text for part in final_parts if hasattr(part, 'text') and part.text
                    )
                    break  # 跳出函數呼叫循環
                
                # --- 如果有函數呼叫，處理它們 ---
                function_turn += 1
                print(f"\n--- Gemini 要求執行 {len(function_calls)} 個函數 (第 {function_turn} 輪) ---")
                
                # 收集本輪所有函數的回應
                function_response_parts = []
                
                # 處理每個函數呼叫
                for i, fc in enumerate(function_calls):
                    tool_name = fc.name
                    args = fc.args or {}
                    print(f"執行工具 {i+1}/{len(function_calls)}: {tool_name}({args})")
                    
                    try:
                        # 呼叫 MCP tool
                        tool_result = await session.call_tool(tool_name, args)
                        print(f"Tool result type: {type(tool_result)}")
                        
                        # 提取回應內容
                        result_text = ""
                        if hasattr(tool_result, 'content') and tool_result.content:
                            if isinstance(tool_result.content, list) and len(tool_result.content) > 0:
                                content_item = tool_result.content[0]
                                if hasattr(content_item, 'text'):
                                    result_text = content_item.text
                                else:
                                    result_text = str(content_item)
                            else:
                                result_text = str(tool_result.content)
                        else:
                            result_text = str(tool_result)
                            
                        print(f"Tool 回應內容: {result_text}")
                        
                        # 建立函數回應部分
                        function_response = {"result": result_text}
                        function_response_part = types.Part.from_function_response(
                            name=tool_name, response=function_response
                        )
                        function_response_parts.append(function_response_part)
                        
                    except Exception as e:
                        print(f"工具執行錯誤: {str(e)}")
                        function_response = {"error": f"Error executing {tool_name}: {str(e)}"}
                        function_response_part = types.Part.from_function_response(
                            name=tool_name, response=function_response
                        )
                        function_response_parts.append(function_response_part)
                
                # 如果有函數回應，將它們發回給 Gemini
                if function_response_parts:
                    print(f"將 {len(function_response_parts)} 個函數執行結果傳回 Gemini...")
                    """
                    # 構建下一次呼叫的完整內容 (stateless 風格)
                    # 順序：原始用戶輸入 -> 模型回應 -> 函數回應
                    contents_for_next_call = contents + [model_content]
                    
                    # 將所有函數回應添加為單個 Content 的多個 parts
                    contents_for_next_call.append(
                        types.Content(role="user", parts=function_response_parts)
                    )
                    
                    # 再次呼叫 Gemini API
                    response = await client.aio.models.generate_content(
                        model=model_config["name"],
                        contents=contents_for_next_call,
                        config=generation_config
                    )
                    
                    # 只傳單一 Content，role="function"
                    #function_content = types.Content(role="function", parts=function_response_parts)
                    
                    for function_response_part in function_response_parts:
                        response = await chat.send_message(
                            message=function_response_part,
                            config=generation_config
                        )
                    """
                    response = await chat.send_message(
                            message=function_response_parts,
                            config=generation_config
                    )
                else:
                    print("處理了函數呼叫請求，但未能產生任何有效的回應部分。終止本輪處理。")
                    break
            
            # 顯示最終回應
            if final_response_text:
                print("\nGemini 最終回應:", final_response_text)
            elif hasattr(response, 'candidates') and response.candidates:
                final_parts = response.candidates[0].content.parts if hasattr(response.candidates[0].content, 'parts') else []
                final_text = "".join(
                    part.text for part in final_parts if hasattr(part, 'text') and part.text
                )
                print("\nGemini 最終回應:", final_text)
            else:
                print("\nGemini 未回傳有效回應")

# --- 主程式 ---
if __name__ == "__main__":
    asyncio.run(run_async_chat()) 