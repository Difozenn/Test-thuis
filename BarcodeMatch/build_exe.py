#!/usr/bin/env python3
"""
BarcodeMatch EXE Builder Script - Updated for accurate and functional builds
"""

import os
import sys
import shutil
import platform
import subprocess
import json
from pathlib import Path
from datetime import datetime

class BarcodeMatchBuilder:
    def __init__(self):
        self.root_dir = Path.cwd()
        self.build_dir = self.root_dir / "build"
        self.dist_dir = self.root_dir / "dist"
        self.assets_dir = self.root_dir / "assets"
        self.is_32bit = sys.maxsize <= 2**32
        self.architecture = "32bit" if self.is_32bit else "64bit"
        self.version = self.get_version()
        
    def get_version(self):
        """Get version from build_info.py if available"""
        try:
            build_info_path = self.root_dir / "build_info.py"
            if build_info_path.exists():
                with open(build_info_path, 'r') as f:
                    content = f.read()
                    # Look for VERSION = "x.x.x" pattern
                    import re
                    match = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', content)
                    if match:
                        return match.group(1)
        except Exception:
            pass
        return None
        
    def check_requirements(self):
        """Check if all required files exist"""
        print("Checking requirements...")
        
        required_files = [
            "main.py",
            "config_utils.py",
            "build_info.py",
            "startup_utils.py",
            "gui/app.py",
            "gui/menu.py",
            "gui/asset_utils.py",
            "gui/splashscreen.py",
            "gui/panels/scanner_panel.py",
            "gui/panels/database_panel.py",
            "gui/panels/help_panel.py",
            "gui/panels/settings_panel.py",
            "gui/panels/import_panel.py",
            "gui/panels/email_panel.py",
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
            # 32-bit specific versions - exact versions for compatibility
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
            # 64-bit versions - more flexible
            packages = [
                "numpy>=1.21.0,<2.0",
                "pandas>=1.3.0,<3.0",
                "openpyxl>=3.0.0",
                "pyodbc>=4.0.0",
                "keyboard>=0.13.5",
                "pyserial>=3.5",
                "Pillow>=9.0.0",
                "requests>=2.28.0",
                "pyinstaller>=5.0",
                "pyinstaller-hooks-contrib>=2023.0"
            ]
        
        # Keep track of failed installations
        failed_packages = []
        
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
                failed_packages.append(package)
        
        if failed_packages:
            print("\nThe following packages failed to install:")
            for pkg in failed_packages:
                print(f"  - {pkg}")
            print("\nYou may need to install these manually.")
        
        return len(failed_packages) == 0
    
    def create_spec_file(self):
        """Create PyInstaller spec file with proper handling of all dependencies"""
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

block_cipher = None
is_32bit = sys.maxsize <= 2**32

# Get absolute paths
ROOT_DIR = Path(r'{self.root_dir}').resolve()
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
        'numpy.tests',
        'tkinter',  # We use our own GUI
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
        exe_name = f"BarcodeMatch{'_32bit' if self.is_32bit else ''}.exe"
        exe_path = self.dist_dir / exe_name
        
        if exe_path.exists():
            print(f"\nExecutable created: {exe_path}")
            print(f"Size: {exe_path.stat().st_size / 1024 / 1024:.2f} MB")
            
            # Create a copy with version if specified
            if hasattr(self, 'version'):
                versioned_name = f"BarcodeMatch_{self.version}{'_32bit' if self.is_32bit else ''}.exe"
                versioned_path = self.dist_dir / versioned_name
                shutil.copy2(exe_path, versioned_path)
                print(f"Versioned copy created: {versioned_path}")
            
            return True
        else:
            print("ERROR: Executable not found after build!")
            # List files in dist directory for debugging
            if self.dist_dir.exists():
                print("\nFiles in dist directory:")
                for file in self.dist_dir.iterdir():
                    print(f"  - {file.name}")
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
        if self.version:
            print(f"Building version: {self.version}")
        
        # Check requirements
        if not self.check_requirements():
            print("\nBuild aborted due to missing requirements.")
            return 1
        
        # Install packages
        response = input("\nInstall/update Python packages? (y/n): ").lower()
        if response == 'y':
            if not self.install_requirements():
                print("\nWARNING: Some packages failed to install.")
                response = input("Continue anyway? (y/n): ").lower()
                if response != 'y':
                    print("Build aborted.")
                    return 1
        
        # Test imports
        if not self.test_imports():
            print("\nERROR: Import test failed!")
            print("Please ensure all required packages are installed correctly.")
            print("\nTip: Try running:")
            if self.is_32bit:
                print("  pip install -r requirements_32bit.txt")
            else:
                print("  pip install -r requirements.txt")
            return 1
        
        # Clean previous builds
        response = input("\nClean previous build directories? (y/n): ").lower()
        if response == 'y':
            self.clean_build_dirs()
        
        # Build executable
        print("\nStarting build process...")
        if self.build_exe():
            print("\n" + "=" * 50)
            print("BUILD SUCCESSFUL!")
            print(f"Executable location: {self.dist_dir}")
            
            # Show all created files
            if self.dist_dir.exists():
                print("\nCreated files:")
                for file in self.dist_dir.iterdir():
                    if file.is_file():
                        size_mb = file.stat().st_size / 1024 / 1024
                        print(f"  - {file.name} ({size_mb:.2f} MB)")
            
            print("=" * 50)
            return 0
        else:
            print("\n" + "=" * 50)
            print("BUILD FAILED!")
            print("\nPlease check the error messages above.")
            print("Common issues:")
            print("  - Missing dependencies")
            print("  - Antivirus blocking PyInstaller")
            print("  - Insufficient disk space")
            print("=" * 50)
            return 1

if __name__ == "__main__":
    # Change to script directory first
    os.chdir(Path(__file__).parent)
    
    builder = BarcodeMatchBuilder()
    sys.exit(builder.run())