#!/usr/bin/env python
"""
Build script for Project Datalog EXE
Comprehensive preparation for all components
"""

import os
import sys
import shutil
import subprocess
import json

def clean_build():
    """Remove old build artifacts"""
    dirs_to_remove = ['build', 'dist', '__pycache__']
    files_to_remove = ['*.pyc', '*.pyo', '*.spec.bak']
    
    print("🧹 Cleaning old build artifacts...")
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            print(f"  Removing {dir_name}/")
            shutil.rmtree(dir_name)
    
    # Clean pycache in subdirectories
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            print(f"  Removing {pycache_path}")
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
    filevers=(1,2,0,0),
    prodvers=(1,2,0,0),
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
        [StringStruct(u'CompanyName', u'Project Datalog Systems'),
        StringStruct(u'FileDescription', u'Project Datalog - Advanced Project Management System'),
        StringStruct(u'FileVersion', u'1.2.0.0'),
        StringStruct(u'InternalName', u'ProjectDatalog'),
        StringStruct(u'LegalCopyright', u'Copyright (C) 2025. All rights reserved.'),
        StringStruct(u'OriginalFilename', u'ProjectDatalog.exe'),
        StringStruct(u'ProductName', u'Project Datalog'),
        StringStruct(u'ProductVersion', u'1.2.0.0')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""
    with open('version_info.txt', 'w', encoding='utf-8') as f:
        f.write(version_info)
    print("✅ Created version_info.txt")

def check_dependencies():
    """Check all required dependencies are installed"""
    print("🔍 Checking Python dependencies...")
    
    # Core dependencies (required for basic functionality)
    core_deps = [
        'tkinter',
        'threading', 
        'requests',
        'serial',
        'flask',
        'werkzeug',
        'jinja2',
        'waitress'
    ]
    
    # Data processing dependencies
    data_deps = [
        'pandas',
        'openpyxl',
        'xlrd',
        'xlwt',
        'xlsxwriter',
        'PyPDF2',
        'pdfplumber'
    ]
    
    # Optional system dependencies
    optional_deps = [
        'pyodbc',
        'PIL',
        'psutil'
    ]
    
    missing_core = []
    missing_data = []
    missing_optional = []
    
    # Check core dependencies
    for dep in core_deps:
        try:
            __import__(dep)
            print(f"  ✅ {dep}")
        except ImportError:
            missing_core.append(dep)
            print(f"  ❌ {dep} (CRITICAL)")
    
    # Check data processing dependencies
    for dep in data_deps:
        try:
            __import__(dep)
            print(f"  ✅ {dep}")
        except ImportError:
            missing_data.append(dep)
            print(f"  ⚠️  {dep} (DATA PROCESSING)")
    
    # Check optional dependencies
    for dep in optional_deps:
        try:
            __import__(dep)
            print(f"  ✅ {dep}")
        except ImportError:
            missing_optional.append(dep)
            print(f"  ⚠️  {dep} (OPTIONAL)")
    
    # Report missing dependencies
    if missing_core:
        print(f"\n❌ CRITICAL: Missing core dependencies: {', '.join(missing_core)}")
        print("Install with: pip install -r requirements.txt")
        sys.exit(1)
    
    if missing_data:
        print(f"\n⚠️  WARNING: Missing data processing: {', '.join(missing_data)}")
        print("Some Excel/PDF features may not work")
    
    if missing_optional:
        print(f"\n⚠️  INFO: Missing optional features: {', '.join(missing_optional)}")
        print("Some advanced features may be limited")
    
    print("✅ Dependency check completed")

def check_project_modules():
    """Check all project modules can be imported"""
    print("🔍 Checking project modules...")
    
    project_modules = [
        # Core utilities
        'config_utils',
        'path_utils',
        
        # GUI system
        'gui.app',
        'gui.menu',
        'gui.utils',
        
        # GUI panels
        'gui.panels.admin_panel',
        'gui.panels.database_panel',
        'gui.panels.help_panel',
        'gui.panels.scanner_panel',
        'gui.panels.settings_panel',
        
        # Database system
        'database.db_log_api',
        
        # Services
        'services.background_import_service',
        'services.excel_processing_functions'
    ]
    
    missing = []
    for module in project_modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError as e:
            missing.append(f"{module}: {str(e)}")
            print(f"  ❌ {module}: {e}")
    
    if missing:
        print(f"\n❌ ERROR: Missing project modules:")
        for module in missing:
            print(f"  - {module}")
        print("\nCheck that all Python files are present and have correct syntax")
        sys.exit(1)
    
    print("✅ All project modules found")

def check_assets():
    """Verify all required assets exist"""
    print("🔍 Checking assets and resources...")
    
    required_assets = [
        # Main application assets
        'assets/ico.ico',
        'assets/Logo.png',
        'assets/database.png',
        'assets/help.png',
        'assets/admin.png',
        'assets/settings.png',
        'assets/scanner.png',
        
        # Web interface assets
        'database/static/header.png',
        'database/static/favicon.ico'
    ]
    
    required_templates = [
        'database/templates/base.html',
        'database/templates/dashboard.html',
        'database/templates/projects.html',
        'database/templates/users.html',
        'database/templates/statistics.html',
        'database/templates/settings.html',
        'database/templates/logs_project.html',
        'database/templates/database.html',
        'database/templates/user_performance.html'
    ]
    
    required_configs = [
        'config.json'
    ]
    
    missing_assets = []
    missing_templates = []
    missing_configs = []
    
    # Check assets
    for asset in required_assets:
        if not os.path.exists(asset):
            missing_assets.append(asset)
            print(f"  ❌ {asset}")
        else:
            print(f"  ✅ {asset}")
    
    # Check templates
    for template in required_templates:
        if not os.path.exists(template):
            missing_templates.append(template)
            print(f"  ❌ {template}")
        else:
            print(f"  ✅ {template}")
    
    # Check configs
    for config in required_configs:
        if not os.path.exists(config):
            missing_configs.append(config)
            print(f"  ❌ {config}")
        else:
            print(f"  ✅ {config}")
    
    # Report results
    total_missing = len(missing_assets) + len(missing_templates) + len(missing_configs)
    
    if missing_configs:
        print(f"\n❌ CRITICAL: Missing configuration files:")
        for config in missing_configs:
            print(f"  - {config}")
        sys.exit(1)
    
    if missing_templates:
        print(f"\n⚠️  WARNING: Missing web templates:")
        for template in missing_templates:
            print(f"  - {template}")
        print("Web interface may not work properly")
    
    if missing_assets:
        print(f"\n⚠️  WARNING: Missing assets:")
        for asset in missing_assets:
            print(f"  - {asset}")
        print("Some UI elements may not display correctly")
    
    if total_missing == 0:
        print("✅ All assets and resources found")
    
    return total_missing == 0

def check_pyinstaller():
    """Check PyInstaller is available"""
    print("🔍 Checking PyInstaller...")
    
    try:
        import PyInstaller
        print(f"  ✅ PyInstaller {PyInstaller.__version__}")
        return True
    except ImportError:
        print("  ❌ PyInstaller not found")
        print("\n❌ ERROR: PyInstaller is required for building")
        print("Install with: pip install pyinstaller")
        sys.exit(1)

def create_optimized_spec():
    """Create optimized PyInstaller spec file"""
    print("📝 Creating optimized spec file...")
    
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-
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
'''
    
    with open('project_datalog.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    print("✅ Created project_datalog.spec")

def build_exe(debug=False):
    """Build the executable"""
    spec_file = 'project_datalog.spec'
    
    # Set console mode for debugging
    if debug:
        print("🚀 Building in DEBUG mode (console enabled)...")
        # Temporarily modify spec file for debug
        with open(spec_file, 'r') as f:
            spec_content = f.read()
        
        spec_content = spec_content.replace('console=False', 'console=True')
        spec_content = spec_content.replace('debug=False', 'debug=True')
        
        debug_spec = 'project_datalog_debug.spec'
        with open(debug_spec, 'w') as f:
            f.write(spec_content)
        
        build_spec = debug_spec
    else:
        print("🚀 Building in PRODUCTION mode...")
        build_spec = spec_file
    
    # Run PyInstaller
    cmd = ['pyinstaller', build_spec, '--clean', '--noconfirm']
    print(f"Running: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("❌ Build failed!")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        sys.exit(1)
    else:
        print("✅ Build successful!")
        
    # Clean up debug spec if created
    if debug and os.path.exists('project_datalog_debug.spec'):
        os.remove('project_datalog_debug.spec')

def post_build():
    """Post-build operations"""
    exe_path = 'dist/ProjectDatalog.exe'
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"\n🎉 Build Complete!")
        print(f"Executable: {exe_path}")
        print(f"Size: {size_mb:.2f} MB")
        
        # Create comprehensive README
        readme_content = """Project Datalog - Installation & Usage Guide

=== INSTALLATION ===

1. Extract all files to a folder of your choice
2. Run ProjectDatalog.exe
3. The application will automatically create necessary folders:
   - database/ (SQLite databases and web interface)
   - logs/ (application logs)
   - backups/ (database backups)

=== FEATURES ===

🖥️  Desktop Application:
- Advanced barcode scanning with multiple scanner support
- Real-time project management and coordination
- Multi-user workflow management
- Background processing services

🌐 Web Interface:
- Modern responsive dashboard at http://localhost:5001
- Project statistics and performance analytics
- User management and reporting
- Real-time activity monitoring

📊 Data Processing:
- Excel file processing (.xlsx/.xls) for NESTING, ACCURA, BOERE workflows
- Automatic color and metadata extraction
- PDF processing and analysis
- MDB database integration

👥 Multi-User Support:
- User-specific configurations and paths
- Efficiency targets and performance tracking
- Team utilization analytics
- Work hours and scheduling management

🔧 Administration:
- Comprehensive settings management
- Database backup and maintenance
- System monitoring and diagnostics
- Configuration import/export

=== SYSTEM REQUIREMENTS ===

- Windows 7 or later (64-bit recommended)
- 4GB RAM minimum, 8GB recommended
- 500MB free disk space
- Microsoft Visual C++ Redistributable (usually pre-installed)

For MDB file processing:
- Microsoft Access Database Engine 2016 Redistributable

=== CONFIGURATION ===

Default Settings:
- Database API: http://localhost:5001
- Web Interface: http://localhost:5001/dashboard
- Default Users: NESTING, ACCURA, OPUS, KL GANNOMAT, BOERE

Scanner Configuration:
- Supports USB and Serial (COM port) scanners
- Configurable baud rates and connection types
- Automatic scanner detection and reconnection

Processing Paths:
- NESTING: C:/Rapporten
- OPUS: C:/OPUS/KORPUS  
- KL GANNOMAT: C:/GANNOMAT
- ACCURA: C:/Rapporten
- BOERE: C:/Rapporten

=== USAGE ===

1. Launch ProjectDatalog.exe
2. Configure your scanner and processing paths in Settings
3. Select your user profile (NESTING, ACCURA, etc.)
4. Start scanning barcodes or processing files
5. Monitor progress in the web interface at http://localhost:5001

=== TROUBLESHOOTING ===

Application Won't Start:
- Check Windows Event Viewer for error details
- Ensure all required directories have write permissions
- Verify antivirus software isn't blocking the executable

Scanner Issues:
- Check COM port settings in Device Manager
- Verify scanner driver installation
- Test with different USB ports

Web Interface Issues:
- Check if port 5001 is available
- Disable Windows Firewall temporarily for testing
- Check logs/ folder for detailed error messages

Performance Issues:
- Ensure adequate free disk space
- Monitor CPU and memory usage in Task Manager
- Check database backup settings (default: daily)

=== SUPPORT ===

For technical support:
- Check the logs/ folder for detailed error information
- Review the web interface diagnostics at /database
- Consult the built-in Help panel in the application

Admin Panel Access:
- Password: sunrise
- Provides advanced configuration and system diagnostics

=== VERSION INFORMATION ===

Project Datalog v1.2.0
Built with Python 3.x and modern web technologies
Optimized for Windows enterprise environments

Copyright (C) 2025. All rights reserved.

=== SECURITY NOTES ===

- This executable may trigger antivirus false positives (common with PyInstaller)
- Add an exception in your antivirus software if needed
- The application only accesses configured directories and network ports
- No data is transmitted outside your local network
"""
        
        with open('dist/README.txt', 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print("✅ Created comprehensive README.txt")
        
        # Create quick start batch file
        batch_content = '''@echo off
echo Starting Project Datalog...
echo.
echo Web interface will be available at: http://localhost:5001
echo.
start ProjectDatalog.exe
echo.
echo If the application doesn't start, check README.txt for troubleshooting.
pause
'''
        
        with open('dist/Start_ProjectDatalog.bat', 'w') as f:
            f.write(batch_content)
        
        print("✅ Created Start_ProjectDatalog.bat launcher")

def prepare_environment():
    """Prepare the build environment"""
    print("🛠️  Preparing build environment...")
    
    # Ensure all directories exist
    required_dirs = [
        'assets',
        'database/templates', 
        'database/static',
        'gui/panels',
        'services'
    ]
    
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            print(f"  ⚠️  Creating missing directory: {dir_path}")
            os.makedirs(dir_path, exist_ok=True)
    
    # Check Python path setup
    project_root = os.path.abspath('.')
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    print("✅ Environment prepared")

def main():
    """Main build process"""
    print("=" * 60)
    print("🚀 PROJECT DATALOG - EXECUTABLE BUILD SYSTEM")
    print("=" * 60)
    
    # Check if running in WSL
    if os.path.exists('/proc/version'):
        try:
            with open('/proc/version', 'r') as f:
                if 'microsoft' in f.read().lower():
                    print("\n⚠️  WARNING: Running in WSL (Windows Subsystem for Linux)")
                    print("Building Windows executables from WSL is not recommended.")
                    print("\nPlease run this script from Windows directly:")
                    print("1. Open Windows Command Prompt or PowerShell")
                    print("2. Navigate to: C:\\Users\\Rob_v\\Desktop\\Test-thuis\\BarcodeMaster")
                    print("3. Run: python build_exe.py")
                    print("\nSee BUILD_INSTRUCTIONS.txt for detailed steps.")
                    sys.exit(1)
        except:
            pass
    
    # Parse arguments
    debug = '--debug' in sys.argv
    console = '--console' in sys.argv or debug  # Force console mode
    clean = '--clean' in sys.argv or True  # Default to clean
    skip_checks = '--skip-checks' in sys.argv
    
    try:
        # Preparation phase
        prepare_environment()
        
        if clean:
            clean_build()
        
        create_version_file()
        create_optimized_spec()
        
        # Validation phase
        if not skip_checks:
            check_dependencies()
            check_project_modules()
            check_assets()
            check_pyinstaller()
        else:
            print("⚠️  Skipping validation checks as requested")
        
        # Build phase
        build_exe(debug=console)
        post_build()
        
        # Success summary
        print("\n" + "=" * 60)
        print("🎉 BUILD PROCESS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\n📁 Output Location: dist/ProjectDatalog.exe")
        print("📖 Documentation: dist/README.txt") 
        print("🚀 Quick Start: dist/Start_ProjectDatalog.bat")
        
        if console:
            print("\n🐛 Console build created with debug output enabled")
        else:
            print("\n✨ Production build created")
        
        print("\n🧪 Testing Recommendations:")
        print("1. Run the executable from dist/ folder")
        print("2. Test barcode scanning functionality")
        print("3. Verify web interface at http://localhost:5001")
        print("4. Check all user profiles and processing types")
        print("5. Test Excel/PDF file processing")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Build interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Build failed with error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()