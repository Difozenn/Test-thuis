#!/usr/bin/env python
"""Debug script to identify app.py issues"""

import sys
import traceback

print("Starting debug...")

try:
    print("1. Testing basic imports...")
    import os
    print("   ✓ os imported")
    import json
    print("   ✓ json imported")
    import socket
    print("   ✓ socket imported")
    
    print("\n2. Testing Flask imports...")
    from flask import Flask
    print("   ✓ Flask imported")
    from flask_sqlalchemy import SQLAlchemy
    print("   ✓ SQLAlchemy imported")
    from flask_login import LoginManager
    print("   ✓ LoginManager imported")
    from flask_bcrypt import Bcrypt
    print("   ✓ Bcrypt imported")
    
    print("\n3. Testing third-party imports...")
    try:
        from watchdog.observers import Observer
        print("   ✓ watchdog imported")
    except ImportError as e:
        print(f"   ✗ watchdog import failed: {e}")
        print("   Run: pip install watchdog")
    
    try:
        import openpyxl
        print("   ✓ openpyxl imported")
    except ImportError as e:
        print(f"   ✗ openpyxl import failed: {e}")
        print("   Run: pip install openpyxl")
    
    try:
        import plotly
        print("   ✓ plotly imported")
    except ImportError as e:
        print(f"   ✗ plotly import failed: {e}")
        print("   Run: pip install plotly")
    
    print("\n4. Testing translations module...")
    try:
        from translations import get_translation, setup_translations, get_available_languages
        print("   ✓ translations module imported")
    except ImportError as e:
        print(f"   ✗ translations import failed: {e}")
        print("   Make sure translations.py exists in the same directory")
    
    print("\n5. Testing app creation...")
    try:
        # Test creating the Flask app
        test_app = Flask(__name__)
        print("   ✓ Flask app created")
        
        # Test database creation
        db = SQLAlchemy()
        print("   ✓ Database object created")
        
    except Exception as e:
        print(f"   ✗ App creation failed: {e}")
        traceback.print_exc()
    
    print("\n6. Checking file structure...")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"   Current directory: {current_dir}")
    
    required_files = ['app.py', 'translations.py']
    for file in required_files:
        file_path = os.path.join(current_dir, file)
        if os.path.exists(file_path):
            print(f"   ✓ {file} exists")
        else:
            print(f"   ✗ {file} NOT FOUND")
    
    # Check for templates directory
    templates_dir = os.path.join(current_dir, 'templates')
    if os.path.exists(templates_dir):
        print(f"   ✓ templates directory exists")
        template_count = len([f for f in os.listdir(templates_dir) if f.endswith('.html')])
        print(f"     Found {template_count} template files")
    else:
        print(f"   ✗ templates directory NOT FOUND")
    
    print("\n7. Attempting to import app module...")
    try:
        import app
        print("   ✓ app module imported successfully")
        
        # Check for key attributes
        if hasattr(app, 'app'):
            print("   ✓ app.app exists")
        else:
            print("   ✗ app.app NOT FOUND")
            
        if hasattr(app, 'initialize_database'):
            print("   ✓ initialize_database function exists")
        else:
            print("   ✗ initialize_database function NOT FOUND")
            
    except Exception as e:
        print(f"   ✗ Failed to import app: {e}")
        traceback.print_exc()
    
    print("\n8. Testing minimal Flask app...")
    try:
        minimal_app = Flask(__name__)
        minimal_app.config['SECRET_KEY'] = 'test-key'
        minimal_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
        minimal_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        @minimal_app.route('/')
        def test():
            return 'Test successful'
        
        print("   ✓ Minimal Flask app created successfully")
        
    except Exception as e:
        print(f"   ✗ Minimal app creation failed: {e}")
        traceback.print_exc()

except Exception as e:
    print(f"\nFATAL ERROR: {e}")
    traceback.print_exc()

print("\nDebug complete. Check the output above for any errors.")
input("\nPress Enter to exit...")