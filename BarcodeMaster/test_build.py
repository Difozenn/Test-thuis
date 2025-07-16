#!/usr/bin/env python
"""
Test script to validate build_exe functionality with latest changes
"""

import os
import sys
import subprocess
import tempfile
import shutil

def test_imports():
    """Test all required imports"""
    print("Testing imports...")
    
    required_imports = [
        'tkinter',
        'threading',
        'requests',
        'serial',
        'pandas',
        'openpyxl',
        'xlrd',
        'xlwt',
        'xlsxwriter',
        'pyodbc',
        'PIL',
        'psutil'
    ]
    
    failed_imports = []
    
    for module in required_imports:
        try:
            __import__(module)
            print(f"✓ {module}")
        except ImportError as e:
            print(f"✗ {module}: {e}")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"\nFailed imports: {failed_imports}")
        return False
    
    print("✓ All imports successful")
    return True

def test_project_modules():
    """Test project-specific modules"""
    print("\nTesting project modules...")
    
    project_modules = [
        'config_utils',
        'path_utils',
        'gui.app',
        'database.db_log_api',
        'services.background_import_service',
        'services.excel_processing_functions'
    ]
    
    failed_modules = []
    
    for module in project_modules:
        try:
            __import__(module)
            print(f"✓ {module}")
        except ImportError as e:
            print(f"✗ {module}: {e}")
            failed_modules.append(module)
    
    if failed_modules:
        print(f"\nFailed project modules: {failed_modules}")
        return False
    
    print("✓ All project modules successful")
    return True

def test_excel_processing():
    """Test Excel processing functionality"""
    print("\nTesting Excel processing...")
    
    try:
        from services.excel_processing_functions import (
            get_sheet_name,
            extract_color_from_excel,
            find_excel_file_for_project,
            parse_excel_for_nesting,
            parse_excel_for_accura,
            parse_excel_for_boere,
            generate_excel_for_accura,
            generate_excel_for_boere
        )
        print("✓ Excel processing functions imported")
        
        # Test basic pandas functionality
        import pandas as pd
        test_df = pd.DataFrame({'test': [1, 2, 3]})
        print("✓ Pandas DataFrame creation")
        
        return True
    except Exception as e:
        print(f"✗ Excel processing test failed: {e}")
        return False

def test_threading():
    """Test threading functionality"""
    print("\nTesting threading...")
    
    try:
        import threading
        import time
        
        def test_thread():
            time.sleep(0.1)
            return True
        
        thread = threading.Thread(target=test_thread)
        thread.start()
        thread.join(timeout=1.0)
        
        print("✓ Threading functionality")
        return True
    except Exception as e:
        print(f"✗ Threading test failed: {e}")
        return False

def test_background_service():
    """Test background service functionality"""
    print("\nTesting background service...")
    
    try:
        from services.background_import_service import BackgroundImportService
        
        # Test service creation
        service = BackgroundImportService()
        print("✓ Background service creation")
        
        # Test configuration loading
        service.load_config()
        print("✓ Configuration loading")
        
        return True
    except Exception as e:
        print(f"✗ Background service test failed: {e}")
        return False

def validate_build_files():
    """Validate build configuration files"""
    print("\nValidating build files...")
    
    required_files = [
        'main.py',
        'barcode_master.spec',
        'build_exe.py',
        'requirements.txt',
        'assets/ico.ico'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
        else:
            print(f"✓ {file_path}")
    
    if missing_files:
        print(f"\nMissing files: {missing_files}")
        return False
    
    print("✓ All required files present")
    return True

def dry_run_pyinstaller():
    """Test PyInstaller without actually building"""
    print("\nTesting PyInstaller dry run...")
    
    try:
        cmd = ['pyinstaller', '--help']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✓ PyInstaller available")
            return True
        else:
            print(f"✗ PyInstaller not working: {result.stderr}")
            return False
    except FileNotFoundError:
        print("✗ PyInstaller not installed")
        return False
    except subprocess.TimeoutExpired:
        print("✗ PyInstaller command timed out")
        return False
    except Exception as e:
        print(f"✗ PyInstaller test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("BarcodeMaster Build Validation")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_project_modules,
        test_excel_processing,
        test_threading,
        test_background_service,
        validate_build_files,
        dry_run_pyinstaller
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            failed += 1
        print()
    
    print("=" * 50)
    print(f"Tests passed: {passed}")
    print(f"Tests failed: {failed}")
    
    if failed == 0:
        print("\n✅ All tests passed! build_exe.py should work correctly.")
        print("\nTo build the executable:")
        print("  python build_exe.py")
        print("  python build_exe.py --debug  # for debug build")
    else:
        print(f"\n❌ {failed} tests failed. Fix these issues before building.")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())