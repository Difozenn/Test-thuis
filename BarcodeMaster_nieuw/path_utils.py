import sys
import os

def get_base_path():
    """
    Returns the base path for bundled resources (read-only).
    This is where assets, icons, and bundled scripts are located.
    """
    if getattr(sys, 'frozen', False):
        # Running as bundled executable - PyInstaller sets sys._MEIPASS
        return sys._MEIPASS
    else:
        # Running from source
        return os.path.abspath(os.path.dirname(__file__))

def get_data_path():
    """
    Returns the base path for writable data files.
    This is where config, database, and logs should be stored.
    """
    if getattr(sys, 'frozen', False):
        # For exe, use the directory where the exe is located
        # This allows config persistence between runs
        return os.path.dirname(sys.executable)
    else:
        # For development, use project root
        return os.path.abspath(os.path.dirname(__file__))

def get_resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    This version normalizes path separators to be safe.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Not in a PyInstaller bundle, use the project root
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__)))

    # Sanitize the relative path to use the OS-specific separator
    # This guards against mixed separators (e.g., 'assets/icon.ico')
    sanitized_relative_path = os.path.join(*relative_path.replace('\\', '/').split('/'))

    return os.path.join(base_path, sanitized_relative_path)

def get_writable_path(relative_path):
    """
    Get absolute path for writable files.
    Use for: config.json, database files, logs, backups
    """
    data_path = get_data_path()
    return os.path.join(data_path, relative_path)

def ensure_writable_dirs():
    """
    Ensure all necessary writable directories exist.
    Call this on application startup.
    """
    dirs_to_create = [
        'database',
        'logs',
        'backup',
        'config'
    ]
    
    for dir_name in dirs_to_create:
        dir_path = get_writable_path(dir_name)
        try:
            os.makedirs(dir_path, exist_ok=True)
        except Exception as e:
            print(f"Warning: Could not create directory {dir_path}: {e}")