import json

CONFIG_PATH = "config.json"

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def sync_model_tool_support(available_models):
    config = load_config()
    if "model_tool_support" not in config:
        config["model_tool_support"] = {}
    changed = False
    for model in available_models:
        if model not in config["model_tool_support"]:
            config["model_tool_support"][model] = True
            changed = True
    if changed:
        save_config(config)
    return config["model_tool_support"]

def set_model_tool_support(model, support):
    config = load_config()
    if "model_tool_support" not in config:
        config["model_tool_support"] = {}
    config["model_tool_support"][model] = support
    save_config(config)

def get_model_tool_support(model):
    config = load_config()
    return config.get("model_tool_support", {}).get(model, True) 