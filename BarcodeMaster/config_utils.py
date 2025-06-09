import os
import json

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')

def get_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(new_data):
    config = get_config()
    config.update(new_data)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=4)

def get_config_value(key, default=None):
    return get_config().get(key, default)

def set_config_value(key, value):
    save_config({key: value})
