# -*- mode: python ; coding: utf-8 -*-

import os
import sys

# Get the directory containing this spec file
ROOT_DIR = os.path.dirname(os.path.abspath(SPEC))

# Simple data collection - include all project files
def collect_project_files():
    """Collect all project files for the executable"""
    datas = []
    
    # Add assets folder
    assets_dir = os.path.join(ROOT_DIR, 'assets')
    if os.path.exists(assets_dir):
        datas.append((assets_dir, 'assets'))
    
    # Add gui folder
    gui_dir = os.path.join(ROOT_DIR, 'gui')
    if os.path.exists(gui_dir):
        datas.append((gui_dir, 'gui'))
    
    # Add services folder  
    services_dir = os.path.join(ROOT_DIR, 'services')
    if os.path.exists(services_dir):
        datas.append((services_dir, 'services'))
    
    # Add database folder
    database_dir = os.path.join(ROOT_DIR, 'database')
    if os.path.exists(database_dir):
        datas.append((database_dir, 'database'))
    
    # Add config files
    config_files = ['config.json', 'version_info.txt']
    for config_file in config_files:
        config_path = os.path.join(ROOT_DIR, config_file)
        if os.path.exists(config_path):
            datas.append((config_path, '.'))
    
    return datas

# Collect project data files
project_datas = collect_project_files()
print(f"Including {len(project_datas)} data file groups")

a = Analysis(
    ['main.py'],
    pathex=[ROOT_DIR],
    binaries=[],
    datas=project_datas,
    hiddenimports=[
        # Only include essential hidden imports that PyInstaller typically misses
        'tkinter',
        'tkinter.ttk', 
        'tkinter.messagebox',
        'tkinter.filedialog',
        '_tkinter',
        
        # PIL essentials
        'PIL._tkinter_finder',
        
        # Project modules (let PyInstaller auto-detect most others)
        'gui.app',
        'path_utils',
        'config_utils',
        'database.db_log_api',
        'services.background_import_service',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude large unnecessary modules to reduce size
        'matplotlib',
        'numpy.distutils',
        'scipy',
        'IPython',
        'jupyter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

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
    upx_exclude=[
        'vcruntime140.dll',
        'msvcp140.dll',
        'api-ms-win-*.dll',
        'ucrtbase.dll',
    ],
    runtime_tmpdir=None,
    console=False, # Disable console for production build
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT_DIR, 'assets', 'ico.ico') if os.path.exists(os.path.join(ROOT_DIR, 'assets', 'ico.ico')) else None,
)
