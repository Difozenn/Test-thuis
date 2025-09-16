#!/usr/bin/env python3
"""
Script to clean up invalid PROJECT_START entries that occur after AFGEMELD events.
These entries are data anomalies that shouldn't exist.
"""

import sqlite3
from datetime import datetime

def fix_invalid_project_starts():
    """Remove PROJECT_START entries that occur after AFGEMELD for the same user/project"""
    
    conn = sqlite3.connect('central_logging.sqlite')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    print("Finding invalid PROJECT_START entries that occur after AFGEMELD...")
    
    # Find all invalid PROJECT_START entries
    c.execute("""
        SELECT 
            ps.rowid as start_rowid,
            ps.timestamp as start_time,
            ps.project,
            ps.user,
            af.timestamp as afgemeld_time,
            ps.id as start_id
        FROM logs ps
        JOIN logs af ON ps.project = af.project AND ps.user = af.user
        WHERE ps.event = 'PROJECT_START'
        AND af.event = 'AFGEMELD'
        AND ps.timestamp > af.timestamp
        ORDER BY ps.project, ps.user, ps.timestamp
    """)
    
    invalid_entries = c.fetchall()
    
    if not invalid_entries:
        print("No invalid PROJECT_START entries found.")
        return
    
    print(f"\nFound {len(invalid_entries)} invalid PROJECT_START entries:")
    print("-" * 80)
    
    # Group by project for better display
    by_project = {}
    for entry in invalid_entries:
        project = entry['project']
        if project not in by_project:
            by_project[project] = []
        by_project[project].append(entry)
    
    # Display findings
    for project, entries in by_project.items():
        print(f"\nProject: {project}")
        for entry in entries:
            time_diff = (datetime.fromisoformat(entry['start_time']) - 
                        datetime.fromisoformat(entry['afgemeld_time'])).total_seconds()
            print(f"  User: {entry['user']}")
            print(f"    AFGEMELD at: {entry['afgemeld_time']}")
            print(f"    Invalid PROJECT_START at: {entry['start_time']} (+{time_diff:.3f}s)")
            print(f"    Row ID to delete: {entry['start_rowid']}")
    
    print("\n" + "=" * 80)
    
    # Delete the invalid entries
    rowids_to_delete = [entry['start_rowid'] for entry in invalid_entries]
    
    print(f"\nDeleting {len(rowids_to_delete)} invalid PROJECT_START entries...")
    
    for rowid in rowids_to_delete:
        c.execute("DELETE FROM logs WHERE rowid = ?", (rowid,))
    
    conn.commit()
    print(f"Successfully deleted {len(rowids_to_delete)} invalid entries.")
    
    # Verify the fix
    print("\nVerifying fix...")
    c.execute("""
        SELECT COUNT(*) as count
        FROM logs ps
        JOIN logs af ON ps.project = af.project AND ps.user = af.user
        WHERE ps.event = 'PROJECT_START'
        AND af.event = 'AFGEMELD'
        AND ps.timestamp > af.timestamp
    """)
    
    remaining = c.fetchone()['count']
    if remaining == 0:
        print("✓ All invalid PROJECT_START entries have been cleaned up.")
    else:
        print(f"⚠ Warning: {remaining} invalid entries still remain.")
    
    conn.close()

if __name__ == "__main__":
    fix_invalid_project_starts()