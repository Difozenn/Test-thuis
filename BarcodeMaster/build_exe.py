#!/usr/bin/env python
"""
Build script for BarcodeMaster EXE
"""

import os
import sys
import shutil
import subprocess

def clean_build():
    """Remove old build artifacts"""
    dirs_to_remove = ['build', 'dist', '__pycache__']
    files_to_remove = ['*.pyc', '*.pyo', '*.spec.bak']
    
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            print(f"Removing {dir_name}...")
            shutil.rmtree(dir_name)
    
    # Clean pycache in subdirectories
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            print(f"Removing {pycache_path}...")
            shutil.rmtree(pycache_path)

def create_version_file():
    """Create version info file for Windows"""
    version_info = """# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx

VSVersionInfo(
  ffi=FixedFileInfo(
    # filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
    # Set not needed items to zero 0. Must always contain 4 elements.
    filevers=(1,0,0,0),
    prodvers=(1,0,0,0),
    # Contains a bitmask that specifies the valid bits 'flags'r
    mask=0x3f,
    # Contains a bitmask that specifies the Boolean attributes of the file.
    flags=0x0,
    # The operating system for which this file was designed.
    # 0x4 - NT and there is no need to change it.
    OS=0x40004,
    # The general type of file.
    # 0x1 - the file is an application.
    fileType=0x1,
    # The function of the file.
    # 0x0 - the function is not defined for this fileType
    subtype=0x0,
    # Creation date and time stamp.
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'Your Company'),
        StringStruct(u'FileDescription', u'BarcodeMaster - Barcode Scanner Management System'),
        StringStruct(u'FileVersion', u'1.0.0.0'),
        StringStruct(u'InternalName', u'BarcodeMaster'),
        StringStruct(u'LegalCopyright', u'Copyright (C) 2024. All rights reserved.'),
        StringStruct(u'OriginalFilename', u'BarcodeMaster.exe'),
        StringStruct(u'ProductName', u'BarcodeMaster'),
        StringStruct(u'ProductVersion', u'1.0.0.0')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""
    with open('version_info.txt', 'w', encoding='utf-8') as f:
        f.write(version_info)
    print("Created version_info.txt")

def check_assets():
    """Verify all required assets exist"""
    required_assets = [
        'assets/ico.ico',
        'assets/Logo.png',
        'assets/database.png',
        'assets/help.png',
        'assets/admin.png',
        'assets/settings.png',
        'assets/scanner.png'
    ]
    
    missing = []
    for asset in required_assets:
        if not os.path.exists(asset):
            missing.append(asset)
    
    if missing:
        print("WARNING: Missing assets:")
        for asset in missing:
            print(f"  - {asset}")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)

def build_exe(debug=False):
    """Build the executable"""
    # Set console mode for debugging
    if debug:
        print("Building in DEBUG mode (console enabled)...")
        # Temporarily modify spec file
        with open('barcode_master.spec', 'r') as f:
            spec_content = f.read()
        
        spec_content = spec_content.replace('console=False', 'console=True')
        spec_content = spec_content.replace('debug=False', 'debug=True')
        
        with open('barcode_master_debug.spec', 'w') as f:
            f.write(spec_content)
        
        spec_file = 'barcode_master_debug.spec'
    else:
        spec_file = 'barcode_master.spec'
    
    # Run PyInstaller
    cmd = ['pyinstaller', spec_file, '--clean']
    print(f"Running: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("Build failed!")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        sys.exit(1)
    else:
        print("Build successful!")
        
    # Clean up debug spec if created
    if debug and os.path.exists('barcode_master_debug.spec'):
        os.remove('barcode_master_debug.spec')

def post_build():
    """Post-build operations"""
    exe_path = 'dist/BarcodeMaster.exe'
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"\nBuild complete!")
        print(f"Executable: {exe_path}")
        print(f"Size: {size_mb:.2f} MB")
        
        # Create a readme for distribution
        readme_content = """BarcodeMaster - Installation Instructions

1. Extract all files to a folder of your choice
2. Run BarcodeMaster.exe
3. On first run, the application will create necessary folders:
   - database/ (for SQLite database)
   - logs/ (for application logs)
   - config.json (for settings)

Requirements:
- Windows 7 or later
- Microsoft Visual C++ Redistributable (usually already installed)
- For MDB processing: Microsoft Access Database Engine

Note: Some antivirus software may flag the executable. This is a false positive
common with PyInstaller executables. You may need to add an exception.

Admin Panel Password: sunrise
"""
        
        with open('dist/README.txt', 'w') as f:
            f.write(readme_content)
        
        print("\nCreated README.txt in dist folder")

def main():
    """Main build process"""
    print("BarcodeMaster EXE Build Script")
    print("=" * 50)
    
    # Parse arguments
    debug = '--debug' in sys.argv
    clean = '--clean' in sys.argv or True  # Default to clean
    
    if clean:
        clean_build()
    
    create_version_file()
    check_assets()
    build_exe(debug=debug)
    post_build()
    
    print("\nBuild process complete!")
    print("\nTo test the executable:")
    print("1. Navigate to the dist/ folder")
    print("2. Run BarcodeMaster.exe")
    print("3. Check for any errors in the console (if debug mode)")

if __name__ == '__main__':
    main()