# Building BarcodeMatch Executables

This document explains how to build BarcodeMatch executables for Windows.

## Prerequisites

- Python 3.8 or higher
- For 32-bit builds: 32-bit Python installation
- All required dependencies (see requirements.txt)

## Building 64-bit Version

1. Install dependencies:
   ```bash
   pip install -r requirements_dev.txt
   ```

2. Run the build script:
   ```bash
   python build_exe.py
   ```

3. The executable will be created in the `dist` folder as `BarcodeMatch.exe`

## Building 32-bit Version

The 32-bit version requires a 32-bit Python installation.

1. Install 32-bit Python (3.8 or 3.9 recommended) from python.org
   - Download the "Windows installer (32-bit)" version

2. Run the 32-bit build script:
   ```bash
   python build_32bit.py
   ```
   
   Or if you have both 64-bit and 32-bit Python installed:
   ```bash
   C:\Python39-32\python.exe build_32bit.py
   ```

3. The script will:
   - Check if you're using 32-bit Python
   - Create requirements_32bit.txt if needed
   - Offer to install 32-bit specific dependencies
   - Build the executable

4. The executable will be created in the `dist` folder as `BarcodeMatch_32bit.exe`

## Build Script Features

The updated build scripts include:

- Automatic Python architecture detection
- Dependency version management for 32-bit compatibility
- Comprehensive file inclusion (assets, config, documentation)
- Better error handling and user feedback
- Version tagging support (reads from build_info.py)
- PyInstaller optimization for smaller executables

## Troubleshooting

### Common Issues

1. **Import errors during build**
   - Make sure all dependencies are installed
   - For 32-bit: Use the exact versions in requirements_32bit.txt

2. **Antivirus blocking PyInstaller**
   - Temporarily disable antivirus during build
   - Add PyInstaller to antivirus exclusions

3. **Missing files in executable**
   - Check that all required files are listed in build_exe.py
   - Verify assets directory exists and contains all needed files

4. **32-bit Python not found**
   - Install 32-bit Python from python.org
   - Make sure to select "Add Python to PATH" during installation

## Dependencies

### Core Dependencies
- numpy: Numerical computing
- pandas: Data manipulation
- openpyxl: Excel file handling
- keyboard: Keyboard input handling
- pyserial: Serial port communication
- Pillow: Image processing
- requests: HTTP requests
- pyodbc: Database connectivity (optional)

### Build Dependencies
- pyinstaller: Creates executables
- pyinstaller-hooks-contrib: Additional hooks for dependencies