# -*- mode: python ; coding: utf-8 -*-
# Project Datalog - Optimized PyInstaller Spec File

import os
import sys

# Get the directory containing this spec file
ROOT_DIR = os.path.dirname(os.path.abspath(SPEC))

def collect_project_files():
    """Collect all project files for the executable"""
    datas = []
    
    # Add assets folder
    assets_dir = os.path.join(ROOT_DIR, 'assets')
    if os.path.exists(assets_dir):
        datas.append((assets_dir, 'assets'))
    
    # Add database folder (templates and static files)
    database_dir = os.path.join(ROOT_DIR, 'database')
    if os.path.exists(database_dir):
        # Add templates
        templates_dir = os.path.join(database_dir, 'templates')
        if os.path.exists(templates_dir):
            datas.append((templates_dir, 'database/templates'))
        
        # Add static files
        static_dir = os.path.join(database_dir, 'static')
        if os.path.exists(static_dir):
            datas.append((static_dir, 'database/static'))
    
    # Add configuration files
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
        # Core GUI
        'tkinter',
        'tkinter.ttk', 
        'tkinter.messagebox',
        'tkinter.filedialog',
        'tkinter.scrolledtext',
        '_tkinter',
        
        # Image processing
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'PIL._tkinter_finder',
        
        # Network and API
        'requests',
        'flask',
        'flask.templating',
        'flask.json',
        'flask.logging',
        'werkzeug',
        'werkzeug.serving',
        'werkzeug.server',
        'jinja2',
        'jinja2.loaders',
        'waitress',
        'waitress.server',
        
        # Serial communication
        'serial',
        'serial.tools',
        'serial.tools.list_ports',
        
        # Data processing
        'pandas',
        'openpyxl',
        'openpyxl.reader.excel',
        'openpyxl.writer.excel',
        'xlrd',
        'xlwt',
        'xlsxwriter',
        'PyPDF2',
        'pdfplumber',
        
        # Database
        'sqlite3',
        'pyodbc',
        
        # System utilities
        'psutil',
        'threading',
        'concurrent.futures',
        'queue',
        'multiprocessing',
        
        # Project modules - Core
        'path_utils',
        'config_utils',
        
        # Project modules - GUI
        'gui.app',
        'gui.menu',
        'gui.utils',
        
        # Project modules - GUI Panels
        'gui.panels',
        'gui.panels.admin_panel',
        'gui.panels.database_panel', 
        'gui.panels.help_panel',
        'gui.panels.scanner_panel',
        'gui.panels.settings_panel',
        
        # Project modules - Database
        'database.db_log_api',
        
        # Project modules - Services
        'services.background_import_service',
        'services.excel_processing_functions'
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
        'notebook',
        'pytest',
        'sphinx',
        'setuptools',
        'distutils'
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
    name='ProjectDatalog',
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
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version_file='version_info.txt',
    icon=os.path.join(ROOT_DIR, 'assets', 'ico.ico') if os.path.exists(os.path.join(ROOT_DIR, 'assets', 'ico.ico')) else None,
)
