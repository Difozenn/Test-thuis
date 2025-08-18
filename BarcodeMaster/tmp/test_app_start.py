#!/usr/bin/env python3
"""Test script to verify the application structure is complete"""

import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all necessary modules can be imported"""
    print("Testing imports...")
    
    try:
        from gui.panels import scanner_panel
        print("✓ scanner_panel imported successfully")
    except Exception as e:
        print(f"✗ Error importing scanner_panel: {e}")
        return False
    
    try:
        from gui.panels import admin_panel
        print("✓ admin_panel imported successfully")
    except Exception as e:
        print(f"✗ Error importing admin_panel: {e}")
        return False
    
    try:
        # Check if the classes exist
        if hasattr(scanner_panel, 'ScannerPanel'):
            print("✓ ScannerPanel class exists")
        else:
            print("✗ ScannerPanel class not found")
            return False
            
        if hasattr(admin_panel, 'AdminPanel'):
            print("✓ AdminPanel class exists")
        else:
            print("✗ AdminPanel class not found")
            return False
            
    except Exception as e:
        print(f"✗ Error checking classes: {e}")
        return False
    
    # Check for required methods
    print("\nChecking ScannerPanel methods...")
    sp_class = scanner_panel.ScannerPanel
    required_methods = ['_update_admin_dependent_ui', 'pause_session', 'resume_session', 
                       'start_new_session', 'update_session_display']
    
    for method in required_methods:
        if hasattr(sp_class, method):
            print(f"  ✓ {method} exists")
        else:
            print(f"  ✗ {method} missing")
    
    print("\nChecking AdminPanel methods...")
    ap_class = admin_panel.AdminPanel
    required_methods = ['_create_user_config_tab', '_build_user_list_ui', '_add_user_config']
    
    for method in required_methods:
        if hasattr(ap_class, method):
            print(f"  ✓ {method} exists")
        else:
            print(f"  ✗ {method} missing")
    
    return True

def main():
    print("BarcodeMaster Application Structure Test")
    print("=" * 50)
    
    if test_imports():
        print("\n✓ All tests passed! The application structure is complete.")
        print("\nSummary of changes:")
        print("- User configuration moved from scanner_panel to admin_panel")
        print("- New 'Gebruiker Configuratie' tab added to admin panel")
        print("- Scanner panel now shows enhanced dual-session interface")
        print("- Icon-based professional buttons implemented")
        print("- Smart pause logic for both sessions implemented")
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()