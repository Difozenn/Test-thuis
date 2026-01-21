import os
import json
import sys
import tempfile
from pathlib import Path

CONFIG_FILENAME = "config.json"
ALT_CONFIG_DIR = os.path.join(os.path.expanduser('~'), '.barcodematch')

def get_base_path():
    """Get the base path for the application, handling both development and frozen states."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        # For onefile mode, the exe extracts to a temp directory
        # We want to save config next to the exe, not in temp
        if hasattr(sys, '_MEIPASS'):
            # This is the temp directory, get the actual exe directory
            return os.path.dirname(sys.executable)
        else:
            return os.path.dirname(sys.executable)
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))

def ensure_config_dir(path):
    """Ensure the directory for config exists"""
    dir_path = os.path.dirname(path)
    if dir_path and not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path, exist_ok=True)
        except Exception as e:
            print(f"[CONFIG] Could not create directory {dir_path}: {e}")

def can_write_to_directory(directory):
    """Test if we can write to a directory"""
    try:
        test_file = os.path.join(directory, '.test_write_' + str(os.getpid()))
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        return True
    except (PermissionError, OSError, IOError):
        return False

def get_config_path():
    """Get the configuration file path with fallback to user directory."""
    base = get_base_path()
    
    # First try: Next to the executable/script
    config_path = os.path.join(base, CONFIG_FILENAME)
    
    # If running as frozen exe, check if we can write to the directory
    if getattr(sys, 'frozen', False):
        if not can_write_to_directory(base):
            # Use alternative directory in user's home
            config_path = os.path.join(ALT_CONFIG_DIR, CONFIG_FILENAME)
            ensure_config_dir(config_path)
            print(f"[CONFIG] Using user directory for config: {config_path}")
        else:
            print(f"[CONFIG] Using exe directory for config: {config_path}")
    else:
        print(f"[CONFIG] Using script directory for config: {config_path}")
    
    return config_path

def load_config():
    """Load configuration from file"""
    config_path = get_config_path()
    
    # Try primary location
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                print(f"[CONFIG] Loaded config from: {config_path}")
                return config
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON in config file {config_path}: {e}")
            # Try to backup the corrupted file
            try:
                backup_path = config_path + '.backup'
                os.rename(config_path, backup_path)
                print(f"[CONFIG] Backed up corrupted config to: {backup_path}")
            except:
                pass
            return {}
        except Exception as e:
            print(f"[ERROR] Failed to load config from {config_path}: {e}")
            return {}
    
    # If frozen, also check the alt directory as fallback
    if getattr(sys, 'frozen', False):
        alt_config_path = os.path.join(ALT_CONFIG_DIR, CONFIG_FILENAME)
        if alt_config_path != config_path and os.path.exists(alt_config_path):
            try:
                with open(alt_config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    print(f"[CONFIG] Loaded config from alt location: {alt_config_path}")
                    return config
            except Exception as e:
                print(f"[ERROR] Failed to load alt config from {alt_config_path}: {e}")
    
    print("[CONFIG] No config file found, using defaults")
    return {}

def update_config(updates):
    """Update configuration file with new values"""
    config_path = get_config_path()
    
    # Load existing config
    config = load_config()
    
    # Update with new values
    config.update(updates)
    
    # Ensure directory exists
    ensure_config_dir(config_path)
    
    # Try to write to config file
    try:
        # Write to temp file first
        temp_fd, temp_path = tempfile.mkstemp(suffix='.tmp', prefix='config_', 
                                              dir=os.path.dirname(config_path))
        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            # Replace original file with temp file
            if os.path.exists(config_path):
                os.remove(config_path)
            os.rename(temp_path, config_path)
            
            print(f"[CONFIG] Successfully saved config to: {config_path}")
            
        except Exception as e:
            # Clean up temp file on error
            try:
                os.close(temp_fd)
                os.remove(temp_path)
            except:
                pass
            raise e
            
    except Exception as e:
        print(f"[ERROR] Failed to save config to {config_path}: {e}")
        
        # Try alternative location if primary fails and we're frozen
        if getattr(sys, 'frozen', False) and not config_path.startswith(ALT_CONFIG_DIR):
            alt_path = os.path.join(ALT_CONFIG_DIR, CONFIG_FILENAME)
            try:
                ensure_config_dir(alt_path)
                with open(alt_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
                print(f"[CONFIG] Config saved to alternative location: {alt_path}")
            except Exception as e2:
                print(f"[ERROR] Failed to save config to alternative location: {e2}")
                raise

def get_setting(key, default=None):
    """Get a single setting from config"""
    config = load_config()
    return config.get(key, default)

def set_setting(key, value):
    """Set a single setting in config"""
    update_config({key: value})