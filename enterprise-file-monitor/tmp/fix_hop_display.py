#!/usr/bin/env python3
"""
Script to fix HOP filename display issues and clear potential caching
Run this on the production server to update old records
"""

import sqlite3
import sys
import os
from datetime import datetime, timedelta

def check_and_fix_database(db_path):
    """Check and potentially fix HOP filename issues in database"""
    print(f"\n{'='*60}")
    print(f"Checking database: {db_path}")
    print(f"{'='*60}")
    
    if not os.path.exists(db_path):
        print(f"ERROR: Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check recent CNC analysis records that might have incorrect filenames
    print("\nChecking for generic filenames that should be HOP files:")
    print("-" * 60)
    
    cursor.execute("""
        SELECT c.id, c.file_path, e.file_path as event_path, c.created_at 
        FROM cnc_analysis c
        JOIN event e ON c.event_id = e.id
        WHERE c.file_path IN ('field1.nc', 'field2.nc', 'field3.nc', 
                             'Field1.nc', 'Field2.nc', 'Field3.nc',
                             'Field1.spf', 'Field2.spf', 'Field3.spf',
                             'ETAP_Volkern_Bureau_1604.hopx')
        ORDER BY c.created_at DESC
        LIMIT 20
    """)
    
    records = cursor.fetchall()
    if records:
        print(f"Found {len(records)} records with generic filenames:")
        for id, file_path, event_path, created_at in records:
            print(f"  ID {id}: {file_path} (Event: {event_path}) - {created_at}")
            
        # Ask if user wants to fix these
        response = input("\nDo you want to attempt to extract HOP filenames from these files? (y/n): ")
        if response.lower() == 'y':
            fix_generic_filenames(conn, cursor, records)
    else:
        print("No records found with generic filenames")
    
    # Check for actual HOP files in the database
    print("\n\nChecking for HOP files already correctly stored:")
    print("-" * 60)
    
    cursor.execute("""
        SELECT c.id, c.file_path, e.file_path as event_path, c.created_at 
        FROM cnc_analysis c
        JOIN event e ON c.event_id = e.id
        WHERE UPPER(c.file_path) LIKE '%.HOP' 
           OR UPPER(c.file_path) LIKE '%.HOPS'
           OR UPPER(c.file_path) LIKE '%.HOPX'
        ORDER BY c.created_at DESC
        LIMIT 10
    """)
    
    hop_records = cursor.fetchall()
    if hop_records:
        print(f"Found {len(hop_records)} records with HOP filenames:")
        for id, file_path, event_path, created_at in hop_records:
            print(f"  ID {id}: {file_path} - {created_at}")
    else:
        print("No HOP filenames found in database")
    
    conn.close()

def fix_generic_filenames(conn, cursor, records):
    """Attempt to fix generic filenames by extracting HOP references from NC files"""
    import re
    
    fixed_count = 0
    
    for id, file_path, event_path, created_at in records:
        # Try to read the actual NC file from the event path
        if event_path and os.path.exists(event_path):
            try:
                with open(event_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(5000)  # Read first 5000 chars for efficiency
                
                # Look for HOP file references
                hop_patterns = [
                    r'([A-Z]:\\\\[^\\\\]+(?:\\\\[^\\\\]+)*\\\\[^\\\\]+\.HOP[SX]?)',
                    r'([\\w_\\-]+\.HOP[SX]?)(?:\\s|$|\"|\\))',
                    r';\\s*---\\s*([^:*?"<>|\\r\\n]+\.HOP[SX]?)',
                ]
                
                hop_found = None
                for pattern in hop_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        # Extract just the filename from full paths
                        hop_filename = matches[0]
                        if '\\' in hop_filename:
                            hop_filename = hop_filename.split('\\')[-1]
                        hop_found = hop_filename
                        break
                
                if hop_found:
                    print(f"  Updating ID {id}: {file_path} -> {hop_found}")
                    cursor.execute("""
                        UPDATE cnc_analysis 
                        SET file_path = ? 
                        WHERE id = ?
                    """, (hop_found, id))
                    fixed_count += 1
                else:
                    print(f"  No HOP file found in {event_path}")
                    
            except Exception as e:
                print(f"  Error reading {event_path}: {e}")
        else:
            print(f"  Event file not found: {event_path}")
    
    if fixed_count > 0:
        conn.commit()
        print(f"\n✅ Fixed {fixed_count} records")
    else:
        print("\n❌ No records were fixed")

def clear_browser_cache_hint():
    """Provide instructions for clearing browser cache"""
    print(f"\n{'='*60}")
    print("Browser Cache Clearing Instructions:")
    print(f"{'='*60}")
    print("""
If the dashboard still shows old filenames after running this script:

1. Clear Browser Cache (Chrome/Edge):
   - Press Ctrl+Shift+Delete
   - Select "Cached images and files"
   - Click "Clear data"
   - OR: Press Ctrl+F5 on the dashboard page

2. Restart Flask App:
   - Stop the Flask app (Ctrl+C)
   - Start it again: python app.py

3. Check Flask App Logs:
   - Look for "[DEBUG] HOP Filename handling:" messages
   - These show what filenames are being received and stored

4. If issue persists, check:
   - Is the C# file monitor app running the latest version?
   - Are there multiple Flask instances running?
   - Is there a reverse proxy caching responses?
""")

def main():
    """Main function"""
    print("HOP Filename Fix Tool")
    print("=" * 60)
    
    # Check for database in common locations
    db_locations = [
        './instance/file_monitor.db',
        './enterprise_monitor.db',
        './monitoring.db',
        '../instance/file_monitor.db',
    ]
    
    db_path = None
    for location in db_locations:
        if os.path.exists(location):
            db_path = location
            break
    
    if db_path:
        check_and_fix_database(db_path)
        clear_browser_cache_hint()
    else:
        print("ERROR: Could not find database file!")
        print("Searched in:", db_locations)
        
        # Allow user to specify path
        custom_path = input("\nEnter database path (or press Enter to exit): ")
        if custom_path and os.path.exists(custom_path):
            check_and_fix_database(custom_path)
            clear_browser_cache_hint()

if __name__ == "__main__":
    main()