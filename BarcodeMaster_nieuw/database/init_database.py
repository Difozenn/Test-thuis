#!/usr/bin/env python3
import sys
import os
sys.path.append('/mnt/c/Users/Rob_v/Desktop/PP/BarcodeMaster/database')

# Import the init_db function from db_log_api
from db_log_api import init_db

print("Initializing database...")
try:
    init_db()
    print("Database initialized successfully!")
except Exception as e:
    print(f"Error initializing database: {e}")
    import traceback
    traceback.print_exc()