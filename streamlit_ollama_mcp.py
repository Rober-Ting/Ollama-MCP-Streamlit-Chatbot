import streamlit as st
import asyncio
from mcpclient_manager import MCPClientManager, get_available_servers, load_config, initialize_agent_and_tools
from ollama_toolmanager import OllamaToolManager
from ollama_agent import OllamaAgent
import ollama
from model_setting import sync_model_tool_support, get_model_tool_support, set_model_tool_support

# 從 streamlit_manager 讀取聊天區塊高度
from streamlit_manager import get_chat_container_height, get_stream_mode
CHAT_CONTAINER_HEIGHT = get_chat_container_height()

async def summarize_tool_result(agent, tool_result, user_prompt):
    """
    將工具回應丟給 LLM，請 LLM 幫忙總結/說明。
    """
    summary_prompt = (
        f"使用者原始問題：{user_prompt}\n"
        f"工具回應如下：\n{tool_result}\n"
        "請用自然語言總結這個工具回應，若有錯誤請友善說明原因並給出建議。"
    )
    async for chunk in agent.get_response(summary_prompt, stream=False):
        return chunk

try:
    # 初始化 session state
    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "mcpclient" not in st.session_state:
        st.session_state.mcpclient = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "connected" not in st.session_state:
        st.session_state.connected = False
    if "selected_model" not in st.session_state:
        st.session_state.selected_model = None
    if "selected_server" not in st.session_state:
        st.session_state.selected_server = None
    if "page" not in st.session_state:
        st.session_state.page = "chat"
    if "selected_mcp_server" not in st.session_state:
        st.session_state.selected_mcp_server = None
    if "processing" not in st.session_state:
        st.session_state.processing = False

    # Sidebar: 選模型、server
    # 全局 sidebar 按鈕字體變大
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] button {
            font-size: 1.2em !important;
            font-weight: bold !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    st.sidebar.title("🦙Ollama MCP Client Setting")
    # 取得本地模型清單
    try:
        available_models_data = ollama.list()
        available_models = [model['model'] for model in available_models_data['models']]
    except Exception as e:
        available_models = []
        st.sidebar.error(f"取得模型失敗: {e}")

    # 同步模型支援狀態
    model_tool_support_dict = sync_model_tool_support(available_models)

    prev_model = st.session_state.get("_prev_selected_model")
    prev_server = st.session_state.get("_prev_selected_server")
    selected_model = st.sidebar.selectbox("Ollama model selection", available_models, key="selected_model")
    servers = get_available_servers()
    selected_server = st.sidebar.selectbox("MCP Server selection", servers, key="selected_server")
    # 若模型或 server 有變動，清除 agent/mcpclient/connected
    if (prev_model is not None and prev_model != selected_model) or (prev_server is not None and prev_server != selected_server):
        st.session_state.agent = None
        st.session_state.mcpclient = None
        st.session_state.connected = False
        st.session_state.chat_history = []
    st.session_state["_prev_selected_model"] = selected_model
    st.session_state["_prev_selected_server"] = selected_server
    model_supports_tool = get_model_tool_support(selected_model)

    if st.sidebar.button("connect/initialize"):
        try:
            agent = initialize_agent_and_tools(selected_model, selected_server, None)
            st.session_state.agent = agent  # 只存 agent（無 async context）
            st.session_state.connected = True
            st.session_state.chat_history = []
            st.sidebar.success("connected!")
        except Exception as e:
            import traceback
            st.session_state.connected = False
            st.session_state.agent = None
            st.sidebar.error(f"❌ MCP server 連線失敗，請確認 server 是否已啟動。\n詳細錯誤: {e}")
            st.sidebar.text(traceback.format_exc())
            

    # 新增 MCP Server 管理按鈕
    st.sidebar.markdown("---")
    if st.sidebar.button("🛠️ MCP Server management"):
        st.session_state.page = "mcp_server"
        st.rerun()
    # 新增 聊天室 切換按鈕
    if st.sidebar.button("💬 Chat room"):
        st.session_state.page = "chat"
        st.rerun()

    # MCP Server management page
    if st.session_state.get("page") == "mcp_server":
        st.title("🛠️ MCP Server management")
        servers = get_available_servers()
        for key in servers:
            if st.button(key, key=key):
                st.session_state.selected_mcp_server = key
                st.session_state.page = "mcp_tools"
                st.rerun()
        st.stop()

    # MCP Tools 頁面
    if st.session_state.get("page") == "mcp_tools":
        server_type = st.session_state.get("selected_mcp_server")
        st.title(f"🔧 MCP Tools @ {server_type}")
        import asyncio
        from mcpclient_manager import MCPClientManager
        async def show_tools():
            try:
                async with MCPClientManager(server_type) as mcpclient:
                    tools = await mcpclient.get_available_tools()
                    if not tools:
                        st.info("此 MCP Server 無可用工具。")
                        return
                    tab_labels = [getattr(tool, 'name', str(tool)) for tool in tools]
                    tabs = st.tabs(tab_labels)
                    for i, tool in enumerate(tools):
                        with tabs[i]:
                            st.subheader("📝 功能描述")
                            st.write(getattr(tool, 'description', ''))
                            st.subheader("🛠️ Input 參數")
                            st.json(getattr(tool, 'inputSchema', {}))
                            st.subheader("📤 Return 內容")
                            output_schema = getattr(tool, 'outputSchema', None)
                            if output_schema:
                                st.json(output_schema)
                            else:
                                st.info("無 outputSchema 定義")
            except Exception as e:
                st.error(f"連線 MCP Server 失敗: {e}")
        asyncio.run(show_tools())
        st.stop()

    # 主畫面
    st.title(" Ollama MCP Client")
    if not st.session_state.connected:
        st.info("Please select the model and MCP server on the left, and click connect/initialize")
        st.stop()

    # 顯示目前狀態（美化版）
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("#### 🦙 目前模型")
        st.markdown(f"<span style='font-size:1.2em;font-weight:bold'>{selected_model}</span>", unsafe_allow_html=True)
        if not model_supports_tool:
            st.markdown("<span style='color:red;font-weight:bold'>❌ <b>無法使用 MCP 工具</b></span>", unsafe_allow_html=True)
        else:
            st.markdown("<span style='color:green;font-weight:bold'>✅ 可使用 MCP 工具</span>", unsafe_allow_html=True)
    with col2:
        st.markdown("#### 🛠️ MCP Server")
        st.markdown(f"<span style='font-size:1.2em;font-weight:bold'>{selected_server}</span>", unsafe_allow_html=True)

    

    # 兩個分頁：即時聊天、歷史紀錄
    tab1, tab2 = st.tabs(["💬 即時聊天", "🕑 歷史紀錄"])

    with tab1:
        chat_container = st.container(height=CHAT_CONTAINER_HEIGHT)
        with chat_container:
            for idx, chat in enumerate(st.session_state.chat_history):
                # 跳過最後一則空的 assistant，讓 streaming 階段來顯示
                if idx == len(st.session_state.chat_history) - 1 and chat["role"] == "assistant" and chat["content"] == "":
                    continue
                with st.chat_message(chat["role"]):
                    if chat["role"] == "user":
                        st.write(chat["content"])
                    else:
                        # assistant 回應，支援工具呼叫顯示
                        if isinstance(chat["content"], dict):
                            tool_call = chat["content"].get("tool_call")
                            tool_result = chat["content"].get("tool_result")
                            final_response = chat["content"].get("final_response")
                            if tool_call:
                                st.markdown(f"🤖 **模型決定呼叫工具**：`{tool_call}`")
                            if tool_result:
                                if "工具執行失敗" in tool_result or "error" in tool_result.lower():
                                    st.error(tool_result)
                                else:
                                    st.markdown(f"🛠️ **工具回應**：`{tool_result}`")
                            if final_response:
                                st.markdown(f"**最終回應**：{final_response}")
                        else:
                            st.write(str(chat["content"]))
        # 輸入框
        col1, col2 = st.columns([6, 1])
        with col1:
            prompt = st.chat_input("請輸入你的問題：", disabled=st.session_state.get("processing", False))
        with col2:
            if st.button("清除", help="清除即時聊天並存入歷史紀錄"):
                if "chat_history_archive" not in st.session_state:
                    st.session_state.chat_history_archive = []
                st.session_state.chat_history_archive.extend(st.session_state.chat_history)
                st.session_state.chat_history = []
                st.rerun()
        if prompt and st.session_state.agent:
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            st.session_state.chat_history.append({"role": "assistant", "content": ""})
            st.session_state["processing"] = True  # 標記正在處理
            st.rerun()  # 先 rerun 讓 user 訊息即時顯示
        # assistant streaming
        if (
            len(st.session_state.chat_history) >= 2 and
            st.session_state.chat_history[-1]["role"] == "assistant" and
            st.session_state.chat_history[-1]["content"] == "" and
            st.session_state.get("processing", False)  # 只有在處理中才執行
        ):
            with st.status("Processing...", expanded=True):
                import asyncio
                stream_mode = get_stream_mode()
                if stream_mode:
                    with chat_container.chat_message("assistant"):
                        ai_placeholder = st.empty()
                        def update(content):
                            st.session_state.chat_history[-1]["content"] = content
                            ai_placeholder.markdown(content)
                        async def stream_agent_response():
                            async for chunk in st.session_state.agent.get_response(st.session_state.chat_history[-2]["content"], stream=True):
                                if isinstance(chunk, dict) and chunk.get("tool_result"):
                                    summary = await summarize_tool_result(
                                        st.session_state.agent,
                                        chunk["tool_result"],
                                        st.session_state.chat_history[-2]["content"]
                                    )
                                    
                                    update(summary)
                                    break
                                else:
                                    update(chunk)
                        asyncio.run(stream_agent_response())
                else:
                    async def get_first_response():
                        agen = st.session_state.agent.get_response(st.session_state.chat_history[-2]["content"], stream=False)
                        async for chunk in agen:
                            if isinstance(chunk, dict) and chunk.get("tool_result"):
                                summary = await summarize_tool_result(
                                    st.session_state.agent,
                                    chunk["tool_result"],
                                    st.session_state.chat_history[-2]["content"]
                                )
                                return summary
                            else:
                                return chunk
                    res = asyncio.run(get_first_response())
                    st.session_state.chat_history[-1]["content"] = res
            st.session_state["processing"] = False  # 清除處理標記
            st.rerun()

    with tab2:
        chat_container2 = st.container(height=CHAT_CONTAINER_HEIGHT)
        with chat_container2:
            for chat in st.session_state.get("chat_history_archive", []):
                with st.chat_message(chat["role"]):
                    st.write(chat["content"])
        if st.button("清除歷史紀錄"):
            st.session_state["chat_history_archive"] = []
            st.rerun()
except Exception as e:
    st.error(f"應用程序錯誤: {str(e)}")
    import traceback
    st.exception(e)
    st.stop() 