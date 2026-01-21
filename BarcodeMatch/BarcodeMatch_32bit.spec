# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

block_cipher = None
is_32bit = sys.maxsize <= 2**32

# Get absolute paths
ROOT_DIR = Path(r'C:\Users\opususer\Desktop\Barcodematch').resolve()
ASSETS_DIR = ROOT_DIR / 'assets'
GUI_DIR = ROOT_DIR / 'gui'
PANELS_DIR = GUI_DIR / 'panels'

# Import hooks for collecting dependencies
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_dynamic_libs

# Collect all dependencies
numpy_datas = collect_data_files('numpy')
pandas_datas = collect_data_files('pandas')
numpy_binaries = collect_dynamic_libs('numpy')
pandas_binaries = collect_dynamic_libs('pandas')
openpyxl_datas = collect_data_files('openpyxl')

# All data files to include
all_datas = [
    # Main assets directory
    (str(ASSETS_DIR), 'assets'),
    # Config file
    (str(ROOT_DIR / 'config.json'), '.'),
    # Version info
    (str(ROOT_DIR / 'version_info.txt'), '.'),
    # Help documentation
    (str(ASSETS_DIR / 'BarcodeMatch_Gebruikershandleiding.pdf'), 'assets'),
]

# Add dependency data files
all_datas.extend(numpy_datas)
all_datas.extend(pandas_datas)
all_datas.extend(openpyxl_datas)

# All hidden imports
hiddenimports = [
    # Core modules
    'config_utils',
    'build_info',
    'startup_utils',
    'session_manager',
    'windows_shutdown',

    # GUI modules
    'gui.app',
    'gui.menu',
    'gui.asset_utils',
    'gui.splashscreen',
    'gui.panels.scanner_panel',
    'gui.panels.database_panel',
    'gui.panels.help_panel',
    'gui.panels.settings_panel',
    'gui.panels.import_panel',
    'gui.panels.email_panel',
    
    # NumPy
    'numpy',
    'numpy.core._multiarray_umath',
    'numpy.core._multiarray_tests',
    'numpy.core._dtype',
    'numpy.core._asarray',
    'numpy.core._ufunc_config',
    'numpy.core._add_newdocs',
    'numpy.core._add_newdocs_scalars',
    'numpy.core._dtype_ctypes',
    'numpy.core._internal',
    'numpy._distributor_init',
    'numpy._globals',
    'numpy.random._pickle',
    
    # Pandas
    'pandas',
    'pandas._libs',
    'pandas._libs.tslibs.np_datetime',
    'pandas._libs.tslibs.nattype',
    'pandas._libs.tslibs.timedeltas',
    'pandas.io.excel._openpyxl',
    
    # Other dependencies
    'openpyxl',
    'openpyxl.cell._writer',
    'PIL',
    'PIL._tkinter_finder',
    'requests',
    'serial',
    'serial.tools',
    'serial.tools.list_ports',
    'serial.tools.list_ports_windows',
    'keyboard',
    'pyodbc',
    
    # Standard library
    'pkg_resources.py2_warn',
    'encodings',
    'encodings.utf_8',
    
    # Tkinter modules
    'tkinter',
    'tkinter.ttk',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'tkinter.font',
    'tkinter.constants',
    '_tkinter',
]

# Add all submodules
hiddenimports.extend(collect_submodules('numpy'))
hiddenimports.extend(collect_submodules('pandas'))
hiddenimports.extend(collect_submodules('openpyxl'))

# Binary files to include
binaries = numpy_binaries + pandas_binaries

# Try to include pyodbc binary if available
try:
    import pyodbc
    pyodbc_path = os.path.dirname(pyodbc.__file__)
    binaries.extend([(os.path.join(pyodbc_path, '*.pyd'), 'pyodbc')])
except ImportError:
    pass

a = Analysis(
    [str(ROOT_DIR / 'main.py')],
    pathex=[str(ROOT_DIR), str(GUI_DIR), str(PANELS_DIR)],
    binaries=binaries,
    datas=all_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        'pandas.tests',
        'numpy.tests',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BarcodeMatch' + ('_32bit' if is_32bit else ''),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=['*.dll', '*.pyd'],  # Don't compress DLLs
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ASSETS_DIR / 'ico.ico') if (ASSETS_DIR / 'ico.ico').exists() else None,
    version=str(ROOT_DIR / 'version_info.txt') if (ROOT_DIR / 'version_info.txt').exists() else None,
)
