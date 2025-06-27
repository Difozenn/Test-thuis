import sys
import os

def get_base_path():
    """
    Returns the base path for the application.
    Handles running from source and as a PyInstaller executable.
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running as a bundled executable (PyInstaller)
        return sys._MEIPASS
    else:
        # Running from source
        return os.path.abspath(os.path.dirname(__file__))

def get_resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    """
    base_path = get_base_path()
    return os.path.join(base_path, relative_path)
