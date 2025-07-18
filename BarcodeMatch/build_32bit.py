#!/usr/bin/env python3
"""
Build script specifically for 32-bit version of BarcodeMatch
This must be run with a 32-bit Python installation!
"""

import sys
import os
import subprocess
from pathlib import Path

def check_python_bitness():
    """Check if we're running 32-bit Python"""
    is_32bit = sys.maxsize <= 2**32
    print(f"Python architecture: {'32-bit' if is_32bit else '64-bit'}")
    print(f"Python version: {sys.version}")
    
    if not is_32bit:
        print("\nERROR: This script must be run with 32-bit Python!")
        print("Please install 32-bit Python and run this script again.")
        print("\nDownload 32-bit Python from:")
        print("https://www.python.org/downloads/windows/")
        print("Look for 'Windows installer (32-bit)'")
        return False
    return True

def find_32bit_python():
    """Try to find 32-bit Python installation"""
    common_paths = [
        r"C:\Python39-32\python.exe",
        r"C:\Python38-32\python.exe",
        r"C:\Python37-32\python.exe",
        r"C:\Python310-32\python.exe",
        r"C:\Python311-32\python.exe",
        r"C:\Program Files (x86)\Python39\python.exe",
        r"C:\Program Files (x86)\Python38\python.exe",
        r"C:\Program Files (x86)\Python37\python.exe",
    ]
    
    for path in common_paths:
        if Path(path).exists():
            # Verify it's actually 32-bit
            try:
                result = subprocess.run(
                    [path, "-c", "import sys; print(sys.maxsize <= 2**32)"],
                    capture_output=True,
                    text=True
                )
                if result.stdout.strip() == "True":
                    return path
            except:
                continue
    
    return None

def main():
    print("BarcodeMatch 32-bit Build Script")
    print("=" * 50)
    
    # Check if we're running 32-bit Python
    if not check_python_bitness():
        # Try to find 32-bit Python
        python_32bit = find_32bit_python()
        if python_32bit:
            print(f"\nFound 32-bit Python at: {python_32bit}")
            print("Re-running this script with 32-bit Python...")
            
            # Re-run this script with 32-bit Python
            script_path = Path(__file__).resolve()
            subprocess.run([python_32bit, str(script_path)] + sys.argv[1:])
            return
        else:
            print("\nCould not find 32-bit Python installation.")
            return
    
    # We're running 32-bit Python, proceed with build
    print("\nRunning main build script...")
    
    # Import and run the main builder
    build_script = Path(__file__).parent / "build_exe.py"
    if not build_script.exists():
        print(f"ERROR: build_exe.py not found at {build_script}")
        return
    
    # Run the main build script
    subprocess.run([sys.executable, str(build_script)])

if __name__ == "__main__":
    main()