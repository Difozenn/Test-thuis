#!/usr/bin/env python3
"""
BarcodeMatch EXE Builder Script - Fixed for Numpy/Pandas issues
"""

import os
import sys
import shutil
import platform
import subprocess
import json
from pathlib import Path

class BarcodeMatchBuilder:
    def __init__(self):
        self.root_dir = Path.cwd()
        self.build_dir = self.root_dir / "build"
        self.dist_dir = self.root_dir / "dist"
        self.assets_dir = self.root_dir / "assets"
        self.is_32bit = sys.maxsize <= 2**32
        self.architecture = "32bit" if self.is_32bit else "64bit"
        
    def check_requirements(self):
        """Check if all required files exist"""
        print("Checking requirements...")
        
        required_files = [
            "main.py",
            "config_utils.py",
            "build_info.py",
            "gui/app.py",
        ]
        
        missing_files = []
        for file in required_files:
            if not (self.root_dir / file).exists():
                missing_files.append(file)
        
        if missing_files:
            print("ERROR: Missing required files:")
            for file in missing_files:
                print(f"  - {file}")
            return False
        
        print("Requirements check passed!")
        return True
    
    def install_requirements(self):
        """Install required packages with correct versions"""
        print(f"\nInstalling requirements for {self.architecture}...")
        
        # First, upgrade pip
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                      capture_output=True)
        
        if self.is_32bit:
            # 32-bit specific versions
            packages = [
                "numpy==1.21.6",  # Last version supporting Python 3.7-3.9 32-bit
                "pandas==1.3.5",  # Compatible with numpy 1.21.6
                "openpyxl==3.0.10",
                "pyodbc==4.0.35",
                "keyboard==0.13.5",
                "pyserial==3.5",
                "Pillow==9.5.0",
                "requests==2.28.2",
                "pyinstaller==5.13.2",
                "pyinstaller-hooks-contrib==2023.10"
            ]
        else:
            # 64-bit versions
            packages = [
                "numpy>=1.21.0",
                "pandas>=1.3.0",
                "openpyxl>=3.0.0",
                "pyodbc>=4.0.0",
                "keyboard>=0.13.5",
                "pyserial>=3.5",
                "Pillow>=9.0.0",
                "requests>=2.28.0",
                "pyinstaller>=5.0",
                "pyinstaller-hooks-contrib>=2023.0"
            ]
        
        for package in packages:
            print(f"Installing {package}...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print(f"Warning: Failed to install {package}")
                print(f"Error: {result.stderr}")
    
    def create_spec_file(self):
        """Create PyInstaller spec file with proper numpy handling"""
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

block_cipher = None
is_32bit = sys.maxsize <= 2**32

# Get absolute paths
ROOT_DIR = Path(r'{self.root_dir}').resolve()
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
    hooksconfig={{}},
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
'''
        
        spec_file = self.root_dir / f"BarcodeMatch_{self.architecture}.spec"
        with open(spec_file, "w", encoding="utf-8") as f:
            f.write(spec_content)
        
        return spec_file
    
    def clean_build_dirs(self):
        """Clean build and dist directories"""
        print("\nCleaning build directories...")
        
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        if self.dist_dir.exists():
            shutil.rmtree(self.dist_dir)
    
    def build_exe(self):
        """Build the executable"""
        print(f"\nBuilding {self.architecture} executable...")
        
        # Create spec file
        spec_file = self.create_spec_file()
        
        # Run PyInstaller
        cmd = [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", str(spec_file)]
        
        print("Running PyInstaller...")
        print(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print("ERROR: Build failed!")
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
            return False
        
        print("Build completed!")
        
        # Check if exe was created
        exe_name = f"BarcodeMatch_{self.architecture}.exe"
        exe_path = self.dist_dir / exe_name
        
        if exe_path.exists():
            print(f"\nExecutable created: {exe_path}")
            print(f"Size: {exe_path.stat().st_size / 1024 / 1024:.2f} MB")
            return True
        else:
            print("ERROR: Executable not found after build!")
            return False
    
    def test_imports(self):
        """Test if all imports work correctly"""
        print("\nTesting imports...")
        
        test_script = """
import sys
print(f"Python: {sys.version}")

try:
    import numpy
    print(f"Numpy: {numpy.__version__}")
except ImportError as e:
    print(f"ERROR importing numpy: {e}")
    sys.exit(1)

try:
    import pandas
    print(f"Pandas: {pandas.__version__}")
except ImportError as e:
    print(f"ERROR importing pandas: {e}")
    sys.exit(1)

try:
    import openpyxl
    print(f"Openpyxl: {openpyxl.__version__}")
except ImportError as e:
    print(f"ERROR importing openpyxl: {e}")
    sys.exit(1)

print("All imports successful!")
"""
        
        result = subprocess.run([sys.executable, "-c", test_script], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"Errors: {result.stderr}")
        
        return result.returncode == 0
    
    def run(self):
        """Run the complete build process"""
        print(f"BarcodeMatch EXE Builder - {self.architecture}")
        print("=" * 50)
        
        print(f"Python version: {sys.version}")
        print(f"Platform: {platform.platform()}")
        print(f"Architecture: {self.architecture}")
        print(f"Working directory: {os.getcwd()}")
        
        # Check requirements
        if not self.check_requirements():
            print("\nBuild aborted due to missing requirements.")
            return 1
        
        # Install packages
        response = input("\nInstall/update Python packages? (y/n): ").lower()
        if response == 'y':
            self.install_requirements()
        
        # Test imports
        if not self.test_imports():
            print("\nERROR: Import test failed!")
            print("Please ensure all required packages are installed correctly.")
            return 1
        
        # Clean previous builds
        self.clean_build_dirs()
        
        # Build executable
        if self.build_exe():
            print("\n" + "=" * 50)
            print("BUILD SUCCESSFUL!")
            print(f"Executable location: {self.dist_dir}")
            print("=" * 50)
            return 0
        else:
            print("\n" + "=" * 50)
            print("BUILD FAILED!")
            print("=" * 50)
            return 1

if __name__ == "__main__":
    # Change to script directory first
    os.chdir(Path(__file__).parent)
    
    builder = BarcodeMatchBuilder()
    sys.exit(builder.run())