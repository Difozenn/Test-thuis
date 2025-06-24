#!/usr/bin/env python
"""
Simple run script for Enterprise File Monitor
"""
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app, initialize_database, create_default_categories
    
    print("Enterprise File Monitor starting...")
    
    # Initialize database
    if not initialize_database():
        print("❌ Failed to initialize database. Exiting.")
        sys.exit(1)
    
    # Create default categories
    create_default_categories()
    
    print("="*50)
    print("Enterprise File Monitor is running!")
    print("URL: http://localhost:5002")
    print("Default login: admin / admin123")
    print("="*50)
    
    # Run the application
    app.run(debug=False, host='0.0.0.0', port=5002, use_reloader=False)
    
except ImportError as e:
    print(f"Import Error: {e}")
    print("Make sure all required dependencies are installed:")
    print("pip install flask flask-sqlalchemy flask-login flask-bcrypt flask-migrate watchdog openpyxl plotly")
    sys.exit(1)
except KeyboardInterrupt:
    print("\nShutting down gracefully...")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    input("Press Enter to exit...")