# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Project Datalog

block_cipher = None

# Analyze main script
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),  # Include assets folder
        ('database/templates', 'database/templates'),  # Include templates
        ('config.json', '.'),  # Include default config if exists
    ],
    hiddenimports=[
        'tkinter',
        'requests',
        'serial',
        'serial.tools.list_ports',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'psutil',
        'pandas',
        'openpyxl',
        'pyodbc',
        'flask',
        'waitress',
        'path_utils',
        'config_utils',
        'gui.app',
        'gui.panels',
        'gui.panels.home_panel',
        'gui.panels.scanner_panel',
        'gui.panels.projects_panel',
        'gui.panels.import_panel',
        'gui.panels.settings_panel',
        'gui.panels.admin_panel',
        'database.db_log_api',
        'services.background_import_service',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',  # Not needed
        'numpy',  # Not needed unless pandas requires it
        'scipy',
        'pytest',
        'notebook',
        'IPython',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Create PYZ archive
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Create EXE
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ProjectDatalog',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Use UPX compression
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/ico.ico',  # Application icon
    version_file=None,  # Add version info if needed
)

# For creating an installer (optional)
# coll = COLLECT(
#     exe,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     name='ProjectDatalog',
# )