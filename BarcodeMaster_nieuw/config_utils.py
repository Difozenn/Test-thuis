import json
import os
from path_utils import get_writable_path

CONFIG_PATH = get_writable_path('config.json')

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
    # Ensure directory exists
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=4)

def get_config_value(key, default=None):
    return get_config().get(key, default)

def set_config_value(key, value):
    save_config({key: value})