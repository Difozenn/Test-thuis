#!/usr/bin/env python3
"""
Diagnostic script to test all imports required by BarcodeMatch
Run this on the secondary computer to identify missing dependencies
"""

import sys
import platform

print("=" * 60)
print("BarcodeMatch Import Diagnostic")
print("=" * 60)
print(f"Python version: {sys.version}")
print(f"Platform: {platform.platform()}")
print(f"Architecture: {'32-bit' if sys.maxsize <= 2**32 else '64-bit'}")
print("=" * 60)

# Track failed imports
failed_imports = []
warnings = []

def test_import(module_name, package_name=None):
    """Test importing a module"""
    if package_name is None:
        package_name = module_name
    
    try:
        module = __import__(module_name)
        version = getattr(module, '__version__', 'Unknown')
        print(f"✓ {package_name}: {version}")
        return True
    except ImportError as e:
        print(f"✗ {package_name}: FAILED - {e}")
        failed_imports.append(package_name)
        return False
    except Exception as e:
        print(f"✗ {package_name}: ERROR - {e}")
        failed_imports.append(package_name)
        return False

print("\nStandard Library Modules:")
print("-" * 30)
test_import("tkinter")
test_import("tkinter.ttk", "tkinter.ttk")
test_import("tkinter.filedialog", "tkinter.filedialog")
test_import("tkinter.messagebox", "tkinter.messagebox")
test_import("json")
test_import("os")
test_import("sys") 
test_import("threading")
test_import("time")
test_import("pathlib")
test_import("tempfile")

print("\nExternal Dependencies:")
print("-" * 30)
test_import("numpy")
test_import("pandas")
test_import("openpyxl")
test_import("pyodbc")
test_import("keyboard")
test_import("serial", "pyserial")
test_import("PIL", "Pillow")
test_import("requests")

print("\nLocal Modules:")
print("-" * 30)
# Test local imports
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

local_modules = [
    ("config_utils", "config_utils.py"),
    ("build_info", "build_info.py"),
    ("startup_utils", "startup_utils.py"),
    ("gui.app", "gui/app.py"),
    ("gui.menu", "gui/menu.py"),
    ("gui.asset_utils", "gui/asset_utils.py"),
    ("gui.splashscreen", "gui/splashscreen.py"),
    ("gui.panels.scanner_panel", "gui/panels/scanner_panel.py"),
    ("gui.panels.database_panel", "gui/panels/database_panel.py"),
    ("gui.panels.help_panel", "gui/panels/help_panel.py"),
    ("gui.panels.settings_panel", "gui/panels/settings_panel.py"),
    ("gui.panels.import_panel", "gui/panels/import_panel.py"),
    ("gui.panels.email_panel", "gui/panels/email_panel.py"),
]

for module_name, file_path in local_modules:
    if os.path.exists(file_path):
        test_import(module_name, file_path)
    else:
        print(f"✗ {file_path}: FILE NOT FOUND")
        failed_imports.append(file_path)

print("\n" + "=" * 60)
if failed_imports:
    print(f"FAILED IMPORTS ({len(failed_imports)}):")
    for imp in failed_imports:
        print(f"  - {imp}")
    print("\nTo fix:")
    print("1. For Python packages, run:")
    print("   pip install -r requirements.txt")
    print("\n2. For tkinter on Linux/WSL:")
    print("   sudo apt-get install python3-tk")
    print("\n3. For missing local files:")
    print("   Ensure all files were copied from the original project")
else:
    print("✓ ALL IMPORTS SUCCESSFUL!")

if warnings:
    print(f"\nWARNINGS ({len(warnings)}):")
    for warning in warnings:
        print(f"  - {warning}")

print("=" * 60)

# Test if we can actually create a tkinter window
if "tkinter" not in failed_imports:
    print("\nTesting tkinter window creation...")
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()  # Hide the window
        root.destroy()
        print("✓ Tkinter window creation successful")
    except Exception as e:
        print(f"✗ Tkinter window creation failed: {e}")
        print("   This might indicate missing display or X11 forwarding issues")