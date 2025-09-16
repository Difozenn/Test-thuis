#!/usr/bin/env python3
"""
Script to fix missing file paths in OPEN events for HOPS and MDB processing.
This will look for Excel files that were generated and update the OPEN events.
"""

import sqlite3
import os

def fix_missing_file_paths():
    """Update OPEN events with missing file paths by finding the generated Excel files"""
    
    conn = sqlite3.connect('central_logging.sqlite')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    print("Finding OPEN events with missing file paths...")
    
    # Find OPEN events without file paths
    c.execute("""
        SELECT DISTINCT 
            l.id,
            l.project,
            l.user,
            l.timestamp,
            l.details
        FROM logs l
        WHERE l.event = 'OPEN'
        AND (l.file_path IS NULL OR l.file_path = '' OR l.file_path = 'None')
        ORDER BY l.timestamp DESC
    """)
    
    missing_paths = c.fetchall()
    
    if not missing_paths:
        print("No OPEN events with missing file paths found.")
        return
    
    print(f"\nFound {len(missing_paths)} OPEN events with missing file paths:")
    print("-" * 80)
    
    updated_count = 0
    
    for entry in missing_paths:
        project = entry['project']
        user = entry['user']
        
        print(f"\nProject: {project}")
        print(f"  User: {user}")
        
        # Try to find a corresponding Excel file from EXCEL_GENERATED events
        c.execute("""
            SELECT file_path 
            FROM logs 
            WHERE project = ? 
            AND user = ? 
            AND event = 'EXCEL_GENERATED'
            AND file_path IS NOT NULL 
            AND file_path != ''
            AND file_path != 'None'
            ORDER BY timestamp DESC
            LIMIT 1
        """, (project, user))
        
        excel_result = c.fetchone()
        
        if excel_result and excel_result['file_path']:
            # Found an Excel file path
            file_path = excel_result['file_path']
            print(f"  Found Excel path: {file_path}")
            
            # Update the OPEN event
            c.execute("""
                UPDATE logs 
                SET file_path = ?
                WHERE id = ?
            """, (file_path, entry['id']))
            
            updated_count += 1
            print(f"  ✓ Updated OPEN event ID {entry['id']}")
        else:
            # Try to construct the path based on user type and project
            if user == 'OPUS':
                # For OPUS, try to find the HOPS folder
                # Extract from details if it contains a path
                details = entry['details'] or ''
                if ';' in details and ('\\' in details or '/' in details):
                    # Extract path from details (format: barcode;path)
                    path_part = details.split(';', 1)[1].strip()
                    if os.path.exists(path_part):
                        folder_path = os.path.dirname(path_part)
                        print(f"  Found HOPS folder from details: {folder_path}")
                        
                        # Look for Excel file in the folder
                        excel_files = [f for f in os.listdir(folder_path) if f.endswith(('.xlsx', '.xls'))]
                        if excel_files:
                            excel_path = os.path.join(folder_path, excel_files[0])
                            c.execute("""
                                UPDATE logs 
                                SET file_path = ?
                                WHERE id = ?
                            """, (excel_path, entry['id']))
                            updated_count += 1
                            print(f"  ✓ Updated with found Excel: {excel_path}")
                        else:
                            # Just store the folder path
                            c.execute("""
                                UPDATE logs 
                                SET file_path = ?
                                WHERE id = ?
                            """, (folder_path, entry['id']))
                            updated_count += 1
                            print(f"  ✓ Updated with folder path: {folder_path}")
                else:
                    print(f"  ⚠ Could not determine path for OPUS")
            elif user == 'KL GANNOMAT':
                # For KL GANNOMAT, look for MDB files
                print(f"  ⚠ MDB path detection not implemented")
            else:
                print(f"  ⚠ No Excel file found for {user}")
    
    conn.commit()
    
    print("\n" + "=" * 80)
    print(f"Updated {updated_count} OPEN events with file paths")
    
    conn.close()

if __name__ == "__main__":
    fix_missing_file_paths()