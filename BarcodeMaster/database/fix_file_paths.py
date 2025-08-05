#!/usr/bin/env python3
"""
Fix file paths in the database that have mixed forward/backward slashes.
Run this script once to normalize all existing file paths.
"""

import sqlite3
import os
import sys

def fix_file_paths():
    """Normalize all file paths in the database."""
    # Get the database path
    db_path = os.path.join(os.path.dirname(__file__), 'central_logging.sqlite')
    
    if not os.path.exists(db_path):
        print(f"Database not found at: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Get all records with file paths
        c.execute("SELECT id, file_path FROM logs WHERE file_path IS NOT NULL AND file_path != ''")
        records = c.fetchall()
        
        fixed_count = 0
        for record_id, file_path in records:
            # Normalize the path
            normalized_path = os.path.normpath(file_path)
            
            # Only update if the path changed
            if normalized_path != file_path:
                c.execute("UPDATE logs SET file_path = ? WHERE id = ?", (normalized_path, record_id))
                fixed_count += 1
                print(f"Fixed: {file_path} -> {normalized_path}")
        
        conn.commit()
        print(f"\nFixed {fixed_count} file paths.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    fix_file_paths()