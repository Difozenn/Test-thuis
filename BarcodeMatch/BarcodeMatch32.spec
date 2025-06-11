# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets\\Logo.png', 'assets'), ('assets\\database.png', 'assets'), ('assets\\email.png', 'assets'), ('assets\\help.png', 'assets'), ('assets\\ico.ico', 'assets'), ('assets\\ico.png', 'assets'), ('assets\\importeren.png', 'assets'), ('assets\\scanner.png', 'assets'), ('assets\\BarcodeMatch_Gebruikershandleiding-converted.html', 'assets'), ('assets\\BarcodeMatch_Gebruikershandleiding.pdf', 'assets')],
    hiddenimports=['requests'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='BarcodeMatch32',
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
    icon=['assets\\ico.ico'],
)
