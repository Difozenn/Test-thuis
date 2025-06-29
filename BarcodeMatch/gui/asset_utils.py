import os
import sys
from pathlib import Path

# Cache for asset paths to avoid repeated filesystem checks
_asset_cache = {}

def get_base_path():
    """Get the base path for assets, handling both development and frozen states."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        # PyInstaller extracts data files to sys._MEIPASS
        base_path = sys._MEIPASS
    else:
        # Running as script - go up one level from gui folder
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    return base_path

def get_asset_path(filename):
    """Get the full path to an asset file, handling both development and frozen states."""
    # Check cache first
    if filename in _asset_cache:
        return _asset_cache[filename]
    
    base_path = get_base_path()
    asset_path = os.path.join(base_path, 'assets', filename)
    
    # Normalize path for consistency
    asset_path = os.path.normpath(asset_path)
    
    # Cache the result
    _asset_cache[filename] = asset_path
    
    # Debug logging in frozen state
    if getattr(sys, 'frozen', False) and os.environ.get('BARCODEMATCH_DEBUG', '').lower() == 'true':
        print(f"[ASSET] Resolved {filename} to {asset_path} (exists: {os.path.exists(asset_path)})")
    
    return asset_path

def get_assets_dir():
    """Get the assets directory path."""
    base_path = get_base_path()
    return os.path.join(base_path, 'assets')

def asset_exists(filename):
    """Check if an asset file exists."""
    asset_path = get_asset_path(filename)
    exists = os.path.exists(asset_path)
    
    # Log missing assets in frozen state
    if getattr(sys, 'frozen', False) and not exists:
        print(f"[ASSET WARNING] Asset not found: {filename} at {asset_path}")
    
    return exists

def list_assets():
    """List all available assets (useful for debugging)"""
    assets_dir = get_assets_dir()
    if os.path.exists(assets_dir):
        return [f for f in os.listdir(assets_dir) if os.path.isfile(os.path.join(assets_dir, f))]
    return []

def verify_required_assets():
    """Verify that all required assets are present"""
    required_assets = [
        'ico.ico',
        'ico.png',
        'Logo.png',
        'importeren.png',
        'scanner.png',
        'email.png',
        'database.png',
        'help.png',
        'settings.png',
        'BarcodeMatch_Gebruikershandleiding.pdf'
    ]
    
    missing = []
    for asset in required_assets:
        if not asset_exists(asset):
            missing.append(asset)
    
    if missing:
        print(f"[ASSET ERROR] Missing required assets: {', '.join(missing)}")
        return False
    
    return True

# Initialize asset verification on import in frozen state
if getattr(sys, 'frozen', False):
    # Only verify in debug mode to avoid startup delays
    if os.environ.get('BARCODEMATCH_DEBUG', '').lower() == 'true':
        verify_required_assets()