import os
import json

def get_config_path():
    """Always return the absolute path to config.json."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def ensure_config_exists():
    config_file = get_config_path()
    if not os.path.exists(config_file):
        default_config = {
            'email_sender': '',
            'email_receiver': '',
            'smtp_server': '',
            'smtp_port': 587,
            'smtp_user': '',
            'smtp_password': '',
            'email_enabled': False,
            'email_send_mode': 'per_scan',
            'default_scanner_type': 'COM',
            'default_scan_mode': 'OPUS',
            'default_base_dir': ''
        }
        try:
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
        except Exception as e:
            print(f"Kon config.json niet aanmaken: {e}")


def update_config(updates):
    """
    Centralized config updater. Reads config.json, merges updates, writes back.
    Args:
        updates (dict): Only the keys to update.
    """
    config_file = get_config_path()
    config = {}
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            try:
                config = json.load(f)
            except Exception:
                config = {}
    config.update(updates)
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=4)
        print(f"[Config] Updated config.json with: {updates}")
    except Exception as e:
        print(f"[Config] Error updating config.json: {e}")

# Ensure config exists on import
ensure_config_exists()
