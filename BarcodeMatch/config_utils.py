import os
import json

CONFIG_FILENAME = "config.json"

def get_config_path():
    base = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base, CONFIG_FILENAME)
    if not os.path.exists(config_path):
        # Try project root
        root_path = os.path.join(base, CONFIG_FILENAME)
        if os.path.exists(root_path):
            return root_path
    return config_path

def load_config():
    config_path = get_config_path()
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}

def update_config(updates):
    config_path = get_config_path()
    config = load_config()
    config.update(updates)
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)
