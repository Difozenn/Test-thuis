# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

block_cipher = None
is_32bit = sys.maxsize <= 2**32

# Get absolute paths
ROOT_DIR = Path(r'C:\Users\Rob_v\Desktop\test-werk-main\BarcodeMatch').resolve()
ASSETS_DIR = ROOT_DIR / 'assets'

# Import hooks for numpy/pandas
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_dynamic_libs

# Collect numpy and pandas completely
numpy_datas = collect_data_files('numpy')
pandas_datas = collect_data_files('pandas')
numpy_binaries = collect_dynamic_libs('numpy')
pandas_binaries = collect_dynamic_libs('pandas')

a = Analysis(
    [str(ROOT_DIR / 'main.py')],
    pathex=[str(ROOT_DIR)],
    binaries=numpy_binaries + pandas_binaries,
    datas=[
        (str(ASSETS_DIR), 'assets'),
    ] + numpy_datas + pandas_datas,
    hiddenimports=[
        'numpy',
        'numpy.core._multiarray_umath',
        'numpy.core._dtype',
        'numpy.core._asarray',
        'numpy.core._ufunc_config',
        'numpy.core._multiarray_tests',
        'numpy.core._add_newdocs',
        'numpy.core._add_newdocs_scalars',
        'numpy.core._dtype_ctypes',
        'numpy.core._internal',
        'numpy.core._string_helpers',
        'numpy.core._struct_ufunc_tests',
        'numpy._distributor_init',
        'numpy._globals',
        'numpy._pytesttester',
        'numpy._version',
        'numpy.random._pickle',
        'pandas',
        'pandas._libs',
        'pandas._libs.tslibs.np_datetime',
        'pandas._libs.tslibs.nattype',
        'pandas._libs.tslibs.timedeltas',
        'pandas._libs.skiplist',
        'pandas.io.excel._openpyxl',
        'openpyxl',
        'PIL._tkinter_finder',
        'requests',
        'serial',
        'serial.tools',
        'serial.tools.list_ports',
        'serial.tools.list_ports_windows',
        'keyboard',
        'pkg_resources.py2_warn',
    ] + collect_submodules('numpy') + collect_submodules('pandas'),
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
    name='BarcodeMatch' + ('_32bit' if is_32bit else '_64bit'),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ASSETS_DIR / 'ico.ico') if (ASSETS_DIR / 'ico.ico').exists() else None,
)
