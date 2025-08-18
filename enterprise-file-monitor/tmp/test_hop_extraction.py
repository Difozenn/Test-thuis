#!/usr/bin/env python3
"""
Test HOP filename extraction with the exact files we have
"""

import os
import re
import sqlite3

def test_hop_extraction_from_file(file_path):
    """Test HOP extraction from a specific file"""
    print(f"\n{'='*60}")
    print(f"Testing file: {file_path}")
    print(f"{'='*60}")
    
    if not os.path.exists(file_path):
        print(f"ERROR: File not found: {file_path}")
        return None
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Look for HOP references - simplified patterns
    hop_patterns = [
        (r'Y:\\\\[^\\s]+\.HOP', 'Full path'),
        (r'[\w_-]+\.HOPX', 'HOPX file'),
        (r'[\w_-]+\.HOPS', 'HOPS file'), 
        (r'[\w_-]+\.HOP', 'HOP file'),
    ]
    
    found_hops = []
    for pattern, desc in hop_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            print(f"\n{desc} matches found:")
            for match in matches[:5]:  # First 5 matches
                # Extract just filename from full paths
                if '\\' in match:
                    filename = match.split('\\')[-1]
                else:
                    filename = match
                print(f"  - {match}")
                if filename not in found_hops:
                    found_hops.append(filename)
    
    if found_hops:
        print(f"\nUnique HOP files found: {found_hops}")
        print(f"Primary HOP file: {found_hops[0]}")
        return found_hops[0]
    else:
        print("No HOP file references found!")
        return None

def check_database_status():
    """Check current database status"""
    db_path = './instance/file_monitor.db'
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return
    
    print(f"\n{'='*60}")
    print("Current Database Status:")
    print(f"{'='*60}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check last 5 CNC analyses
    cursor.execute("""
        SELECT c.id, c.file_path, e.file_path as event_file, c.created_at
        FROM cnc_analysis c
        JOIN event e ON c.event_id = e.id
        ORDER BY c.created_at DESC
        LIMIT 5
    """)
    
    print("\nLast 5 CNC Analysis Records:")
    for id, display_name, event_file, created_at in cursor.fetchall():
        print(f"  ID {id}: Display='{display_name}' | Event='{os.path.basename(event_file) if event_file else 'N/A'}' | {created_at}")
    
    conn.close()

def simulate_c_sharp_logic(file_path):
    """Simulate what the C# app does"""
    print(f"\n{'='*60}")
    print(f"Simulating C# HOP extraction logic for: {file_path}")
    print(f"{'='*60}")
    
    filename = os.path.basename(file_path)
    filename_no_ext = os.path.splitext(filename)[0]
    
    print(f"Filename: {filename}")
    print(f"Filename without extension: {filename_no_ext}")
    
    # Check if filename is generic (like C# does)
    is_generic = (
        filename_no_ext.lower().startswith("field") or
        filename_no_ext.lower().startswith("ultrathink") or
        len(filename_no_ext) < 5
    )
    
    print(f"Is generic filename: {is_generic}")
    
    if is_generic:
        # Extract HOP file
        hop_file = test_hop_extraction_from_file(file_path)
        if hop_file:
            print(f"\n✅ C# would send display name: {hop_file}")
            return hop_file
        else:
            print(f"\n❌ C# would send original name: {filename}")
            return filename
    else:
        print(f"\n✅ C# would send original name: {filename}")
        return filename

def main():
    """Main test function"""
    print("HOP Filename Extraction Test")
    print("=" * 60)
    
    # Test files we have
    test_files = [
        'opus.nc',
        'opus_6_45.nc', 
        'nesting_9_50.NC',
        'nesting_12_10.NC',
        'Field1.spf',
        'Field2.spf',
        'Field2.nc',
        'Field3.nc'
    ]
    
    results = {}
    
    for file in test_files:
        if os.path.exists(file):
            print(f"\n\n{'#'*60}")
            print(f"# Testing: {file}")
            print(f"{'#'*60}")
            
            display_name = simulate_c_sharp_logic(file)
            results[file] = display_name
        else:
            print(f"\nSkipping {file} - file not found")
    
    # Summary
    print(f"\n\n{'='*60}")
    print("SUMMARY - Expected Display Names:")
    print(f"{'='*60}")
    for file, display in results.items():
        print(f"  {file:20} -> {display}")
    
    # Check database
    check_database_status()
    
    print(f"\n{'='*60}")
    print("NEXT STEPS:")
    print(f"{'='*60}")
    print("""
1. Run this test on your production server
2. Compare the results with what you see in the dashboard
3. If display names are wrong in dashboard but correct here:
   - Clear browser cache (Ctrl+F5)
   - Restart Flask app
   - Check if multiple Flask instances are running
4. If extraction fails here too:
   - Check if the NC files have HOP references
   - Send me the content of the files that fail
""")

if __name__ == "__main__":
    main()