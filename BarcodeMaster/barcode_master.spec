# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

# Get the current directory
current_dir = Path(os.getcwd())

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[str(current_dir)],
    binaries=[],
    datas=[
        # Include configuration files
        ('config.json', '.'),
        ('config.ini', '.'),
        # Include assets directory and all its contents
        ('assets', 'assets'),
        # Include database directory structure
        ('database', 'database'),
        # Include GUI directory
        ('gui', 'gui'),
        # Include services directory
        ('services', 'services'),
        # Include logs directory if it exists
        ('logs', 'logs') if os.path.exists('logs') else None,
    ],
    hiddenimports=[
        # GUI modules
        'gui.app',
        'gui.panels.admin_panel',
        'gui.panels.database_panel',
        'gui.panels.scanner_panel',
        # Core modules
        'config_utils',
        'database_manager',
        'path_utils',
        'com_splitter',
        'startup_manager',
        'config_manager',
        # Database modules
        'database.db_log_api',
        # Services
        'services.background_import_service',
        # Third-party modules that might not be auto-detected
        'PIL._tkinter_finder',
        'pkg_resources.py2_warn',
        'waitress',
        'flask',
        'requests',
        'pandas',
        'openpyxl',
        'pyodbc',
        'psutil',
        'serial',
        'serial.tools.list_ports',
        # Tkinter related
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Only exclude truly unnecessary modules
        'matplotlib',
        'numpy.distutils',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Filter out None values from datas
a.datas = [item for item in a.datas if item is not None]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BarcodeMaster',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True for debugging, False for release
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(current_dir / 'assets' / 'ico.ico') if (current_dir / 'assets' / 'ico.ico').exists() else None,
)
