#!/usr/bin/env python3
"""
Debug script to identify HOP filename extraction issues
Run this on the production server to see what's happening
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta

def check_database_records(db_path):
    """Check recent CNC analysis records in the database"""
    print(f"\n{'='*60}")
    print(f"Checking database: {db_path}")
    print(f"{'='*60}")
    
    if not os.path.exists(db_path):
        print(f"ERROR: Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check recent CNC analysis records
    print("\nRecent CNC Analysis Records (last 10):")
    print("-" * 60)
    
    cursor.execute("""
        SELECT c.id, c.file_path, c.cycle_time_seconds, c.machine_time_minutes, 
               c.created_at, e.file_path as event_file
        FROM cnc_analysis c
        LEFT JOIN event e ON c.event_id = e.id
        ORDER BY c.created_at DESC 
        LIMIT 10
    """)
    
    records = cursor.fetchall()
    for record in records:
        id, file_path, cycle_time, machine_time, created_at, event_file = record
        print(f"ID: {id}")
        print(f"  Created: {created_at}")
        print(f"  File: {file_path}")
        print(f"  Event File: {event_file}")
        print(f"  Cycle Time: {cycle_time}s")
        print(f"  Machine Time: {machine_time}min")
        print()
    
    # Check for file path analysis patterns
    print("\nChecking file path patterns in recent CNC analyses:")
    print("-" * 60)
    
    cursor.execute("""
        SELECT file_path, COUNT(*) as count
        FROM cnc_analysis
        WHERE created_at > datetime('now', '-7 days')
        GROUP BY file_path
        ORDER BY count DESC
        LIMIT 10
    """)
    
    path_counts = cursor.fetchall()
    if path_counts:
        for file_path, count in path_counts:
            print(f"  {count}x: {file_path}")
    else:
        print("No recent CNC analyses found")
    
    conn.close()

def check_recent_events(db_path):
    """Check recent events to see what's being received"""
    print(f"\n{'='*60}")
    print("Recent Events (last 10):")
    print(f"{'='*60}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT e.id, e.file_path, e.timestamp, e.event_type, c.id as cnc_id
        FROM event e
        LEFT JOIN cnc_analysis c ON c.event_id = e.id
        ORDER BY e.timestamp DESC
        LIMIT 10
    """)
    
    events = cursor.fetchall()
    for id, file_path, timestamp, event_type, cnc_id in events:
        print(f"\nEvent ID: {id}")
        print(f"  Timestamp: {timestamp}")
        print(f"  File: {file_path}")
        print(f"  Type: {event_type}")
        print(f"  Has CNC Analysis: {'Yes' if cnc_id else 'No'}")
    
    conn.close()

def check_file_extraction(test_file):
    """Test HOP extraction on a specific file"""
    print(f"\n{'='*60}")
    print(f"Testing HOP extraction on: {test_file}")
    print(f"{'='*60}")
    
    if not os.path.exists(test_file):
        print(f"ERROR: File not found: {test_file}")
        return
    
    with open(test_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Look for HOP references
    import re
    hop_patterns = [
        (r'([A-Z]:\\[^\\]+(?:\\[^\\]+)*\\[^\\]+\.HOP[SX]?)', 'Full path'),
        (r'([\w_\-]+\.HOP[SX]?)(?:\s|$|"|\))', 'Standalone'),
        (r';\s*---\s*([^:*?"<>|\r\n]+\.HOP[SX]?)', 'In comment'),
    ]
    
    found_any = False
    for pattern, desc in hop_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            print(f"\n{desc} matches:")
            for match in matches[:5]:  # First 5 matches
                print(f"  - {match}")
            found_any = True
    
    if not found_any:
        print("No HOP file references found!")
        
        # Show first few lines to debug
        print("\nFirst 20 lines of file:")
        lines = content.split('\n')[:20]
        for i, line in enumerate(lines, 1):
            if '.hop' in line.lower():
                print(f"  {i}: >>> {line[:100]}...")
            else:
                print(f"  {i}: {line[:100]}...")

def main():
    """Main debug function"""
    print("HOP Filename Extraction Debug Tool")
    print("=" * 60)
    
    # Check for database in common locations
    db_locations = [
        './instance/file_monitor.db',
        './enterprise_monitor.db',
        './monitoring.db',
        './database/central_logging.sqlite',
        './database/central_logging.db',
        '../database/central_logging.sqlite',
        '../database/central_logging.db',
        './central_logging.sqlite',
        './central_logging.db'
    ]
    
    db_path = None
    for location in db_locations:
        if os.path.exists(location):
            db_path = location
            break
    
    if db_path:
        check_database_records(db_path)
        check_recent_events(db_path)
    else:
        print("ERROR: Could not find database file!")
        print("Searched in:", db_locations)
    
    # Test specific file if provided
    import sys
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        check_file_extraction(test_file)
    else:
        print("\nTip: Run with a CNC file path to test extraction:")
        print(f"  python {sys.argv[0]} /path/to/file.NC")

if __name__ == "__main__":
    main()