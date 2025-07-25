#!/usr/bin/env python3
"""
Build script specifically for 32-bit version of BarcodeMatch
This must be run with a 32-bit Python installation!
"""

import sys
import os
import subprocess
from pathlib import Path
import platform

def check_python_bitness():
    """Check if we're running 32-bit Python"""
    is_32bit = sys.maxsize <= 2**32
    print(f"Python architecture: {'32-bit' if is_32bit else '64-bit'}")
    print(f"Python version: {sys.version}")
    print(f"Platform: {platform.platform()}")
    
    if not is_32bit:
        print("\nERROR: This script must be run with 32-bit Python!")
        print("Please install 32-bit Python and run this script again.")
        print("\nDownload 32-bit Python from:")
        print("https://www.python.org/downloads/windows/")
        print("Look for 'Windows installer (32-bit)'")
        print("\nRecommended versions for 32-bit builds:")
        print("  - Python 3.9.x (32-bit)")
        print("  - Python 3.8.x (32-bit)")
        return False
    return True

def find_32bit_python():
    """Try to find 32-bit Python installation"""
    common_paths = [
        # Common 32-bit Python locations
        r"C:\Python39-32\python.exe",
        r"C:\Python38-32\python.exe",
        r"C:\Python37-32\python.exe",
        r"C:\Python310-32\python.exe",
        r"C:\Python311-32\python.exe",
        r"C:\Python312-32\python.exe",
        
        # Program Files (x86) locations
        r"C:\Program Files (x86)\Python39\python.exe",
        r"C:\Program Files (x86)\Python38\python.exe",
        r"C:\Program Files (x86)\Python37\python.exe",
        r"C:\Program Files (x86)\Python310\python.exe",
        r"C:\Program Files (x86)\Python311\python.exe",
        
        # User installations
        os.path.expanduser(r"~\AppData\Local\Programs\Python\Python39-32\python.exe"),
        os.path.expanduser(r"~\AppData\Local\Programs\Python\Python38-32\python.exe"),
        os.path.expanduser(r"~\AppData\Local\Programs\Python\Python310-32\python.exe"),
    ]
    
    # Also check PATH for python installations
    try:
        # Try to find python installations in PATH
        result = subprocess.run(["where", "python"], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line and line not in common_paths:
                    common_paths.append(line)
    except:
        pass
    
    found_pythons = []
    
    for path in common_paths:
        if Path(path).exists():
            # Verify it's actually 32-bit
            try:
                result = subprocess.run(
                    [path, "-c", "import sys; print(f'{sys.version}|{sys.maxsize <= 2**32}')"],
                    capture_output=True,
                    text=True
                )
                output = result.stdout.strip()
                if output.endswith('|True'):
                    version_info = output.split('|')[0].split()[0]
                    found_pythons.append((path, version_info))
            except:
                continue
    
    if found_pythons:
        print("\nFound 32-bit Python installations:")
        for i, (path, version) in enumerate(found_pythons):
            print(f"{i+1}. Python {version} at {path}")
        
        if len(found_pythons) == 1:
            return found_pythons[0][0]
        else:
            # Let user choose
            try:
                choice = int(input("\nSelect Python installation (enter number): "))
                if 1 <= choice <= len(found_pythons):
                    return found_pythons[choice-1][0]
            except:
                pass
            
            # Default to first found
            return found_pythons[0][0]
    
    return None

def create_requirements_file():
    """Create requirements_32bit.txt if it doesn't exist"""
    req_file = Path("requirements_32bit.txt")
    if not req_file.exists():
        print("\nCreating requirements_32bit.txt...")
        content = """# 32-bit specific versions - MUST use these exact versions
numpy==1.21.6
pandas==1.3.5
openpyxl==3.0.10
pyodbc==4.0.35
keyboard==0.13.5
pyserial==3.5
Pillow==9.5.0
requests==2.28.2

# Build tools
pyinstaller==5.13.2
pyinstaller-hooks-contrib==2023.10
"""
        with open(req_file, 'w') as f:
            f.write(content)
        print("Created requirements_32bit.txt")

def main():
    print("BarcodeMatch 32-bit Build Script")
    print("=" * 50)
    
    # Check if we're running 32-bit Python
    if not check_python_bitness():
        # Try to find 32-bit Python
        python_32bit = find_32bit_python()
        if python_32bit:
            print(f"\nUsing 32-bit Python at: {python_32bit}")
            response = input("Re-run this script with 32-bit Python? (y/n): ").lower()
            if response == 'y':
                print("Re-running with 32-bit Python...")
                
                # Re-run this script with 32-bit Python
                script_path = Path(__file__).resolve()
                result = subprocess.run([python_32bit, str(script_path)] + sys.argv[1:])
                sys.exit(result.returncode)
        else:
            print("\nCould not find 32-bit Python installation.")
            print("\nTo build 32-bit version, you need to:")
            print("1. Install 32-bit Python (3.8 or 3.9 recommended)")
            print("2. Run this script with the 32-bit Python interpreter")
            print("\nExample:")
            print("  C:\\Python39-32\\python.exe build_32bit.py")
            sys.exit(1)
    
    # We're running 32-bit Python, proceed with build
    print("\n✓ Running with 32-bit Python")
    print("\nChecking build environment...")
    
    # Create requirements file if needed
    create_requirements_file()
    
    # Check if build_exe.py exists
    build_script = Path(__file__).parent / "build_exe.py"
    if not build_script.exists():
        print(f"ERROR: build_exe.py not found at {build_script}")
        sys.exit(1)
    
    print("✓ build_exe.py found")
    
    # Ask if user wants to install requirements first
    response = input("\nInstall 32-bit requirements before building? (recommended) (y/n): ").lower()
    if response == 'y':
        print("\nInstalling 32-bit requirements...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements_32bit.txt"],
            capture_output=False
        )
        if result.returncode != 0:
            print("\nERROR: Failed to install requirements")
            response = input("Continue anyway? (y/n): ").lower()
            if response != 'y':
                sys.exit(1)
    
    # Run the main build script
    print("\nStarting 32-bit build process...")
    print("-" * 50)
    
    result = subprocess.run([sys.executable, str(build_script)])
    
    # Exit with the same code as the build script
    sys.exit(result.returncode)

if __name__ == "__main__":
    # Change to script directory
    os.chdir(Path(__file__).parent)
    main()