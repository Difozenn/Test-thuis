import configparser
import os
from path_utils import get_writable_path

CONFIG_FILE = get_writable_path('config.ini')

def get_config():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    return config

def ensure_config_exists():
    if not os.path.exists(CONFIG_FILE):
        # Ensure directory exists
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        config = configparser.ConfigParser()
        config['Startup'] = {
            'start_db_api_on_boot': 'false',
            'start_com_splitter_on_boot': 'false'
        }
        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)

def get_startup_settings():
    ensure_config_exists()
    config = get_config()
    start_db = config.getboolean('Startup', 'start_db_api_on_boot', fallback=False)
    start_splitter = config.getboolean('Startup', 'start_com_splitter_on_boot', fallback=False)
    return start_db, start_splitter

def save_startup_setting(key, value):
    ensure_config_exists()
    config = get_config()
    if 'Startup' not in config:
        config['Startup'] = {}
    config.set('Startup', key, str(value).lower())
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)