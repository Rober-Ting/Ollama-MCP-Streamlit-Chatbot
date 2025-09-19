import json

def get_chat_container_height():
    """
    從 config.json 讀取聊天區塊高度設定，若無則回傳預設值 500。
    """
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        return config.get("UI_Settings", {}).get("CHAT_CONTAINER_HEIGHT", 500)
    except Exception:
        return 500

def get_stream_mode():
    """
    取得 stream_mode 設定，從 config.json 讀取 UI_Settings.STREAM_MODE，預設為 True。
    """
    
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        return config.get("UI_Settings", {}).get("STREAM_MODE", True)
    except Exception:
        return True 