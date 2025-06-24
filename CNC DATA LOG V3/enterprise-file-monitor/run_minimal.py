#!/usr/bin/env python
"""Minimal run script with error handling"""

import sys
import os

print("Enterprise File Monitor - Starting...")

try:
    # First, let's check if all required files exist
    required_files = ['app.py', 'translations.py']
    for file in required_files:
        if not os.path.exists(file):
            print(f"ERROR: Required file '{file}' not found!")
            print(f"Current directory: {os.getcwd()}")
            print(f"Files in directory: {os.listdir('.')}")
            input("Press Enter to exit...")
            sys.exit(1)
    
    print("✓ All required files found")
    
    # Try importing with detailed error messages
    try:
        print("Importing Flask and extensions...")
        from flask import Flask
        from flask_sqlalchemy import SQLAlchemy
        from flask_login import LoginManager
        from flask_bcrypt import Bcrypt
        print("✓ Flask imports successful")
    except ImportError as e:
        print(f"ERROR: Failed to import Flask components: {e}")
        print("\nPlease install required packages:")
        print("pip install flask flask-sqlalchemy flask-login flask-bcrypt")
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Try importing the app
    try:
        print("Importing app module...")
        from app import app, db, check_and_migrate_database, create_default_categories, start_file_monitor
        print("✓ App module imported successfully")
    except ImportError as e:
        print(f"ERROR: Failed to import from app.py: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error importing app: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Initialize database
    print("Initializing database...")
    with app.app_context():
        try:
            # Check and migrate database
            if not check_and_migrate_database():
                print("❌ Database migration failed.")
                input("Press Enter to exit...")
                sys.exit(1)
            
            # Create tables
            db.create_all()
            print("✓ Database tables created")
            
            # Create backup directories
            os.makedirs('reports/backups', exist_ok=True)
            os.makedirs('reports/backups/temp', exist_ok=True)
            print("✓ Backup directories created")
            
            # Create default admin
            from app import User
            if not User.query.filter_by(role='admin').first():
                admin = User(
                    username='admin',
                    email='admin@example.com',
                    role='admin'
                )
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
                print("✓ Default admin user created: admin/admin123")
            else:
                print("✓ Admin user already exists")
            
            # Create default categories
            create_default_categories()
            print("✓ Default categories created")
            
            # Start file monitor
            print("Starting file monitor...")
            start_file_monitor()
            print("✓ File monitor started")
            
        except Exception as e:
            print(f"ERROR during initialization: {e}")
            import traceback
            traceback.print_exc()
            input("Press Enter to exit...")
            sys.exit(1)
    
    # Run the app
    print("\n" + "="*50)
    print("Enterprise File Monitor is running!")
    print("URL: http://localhost:5002")
    print("Default login: admin / admin123")
    print("="*50 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5002, use_reloader=False)
    
except KeyboardInterrupt:
    print("\nShutting down...")
    try:
        from app import stop_file_monitor
        stop_file_monitor()
    except:
        pass
except Exception as e:
    print(f"\nFATAL ERROR: {e}")
    import traceback
    traceback.print_exc()
    input("\nPress Enter to exit...")
    sys.exit(1)