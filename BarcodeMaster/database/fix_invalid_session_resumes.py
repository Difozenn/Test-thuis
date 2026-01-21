#!/usr/bin/env python3
"""
Script to clean up invalid SESSION_RESUME entries that occur after AFGEMELD events.
These entries are data anomalies that shouldn't exist.
"""

import sqlite3
from datetime import datetime

def fix_invalid_session_resumes():
    """Remove SESSION_RESUME entries that occur after AFGEMELD for the same user/project"""
    
    conn = sqlite3.connect('central_logging.sqlite')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    print("Finding invalid SESSION_RESUME entries that occur after AFGEMELD...")
    
    # Find all invalid SESSION_RESUME entries
    c.execute("""
        SELECT 
            sr.rowid as resume_rowid,
            sr.id as resume_id,
            sr.timestamp as resume_time,
            sr.project,
            sr.user,
            af.timestamp as afgemeld_time,
            sr.details
        FROM logs sr
        JOIN logs af ON sr.project = af.project AND sr.user = af.user
        WHERE sr.event = 'SESSION_RESUME'
        AND af.event = 'AFGEMELD'
        AND sr.timestamp > af.timestamp
        ORDER BY sr.project, sr.user, sr.timestamp
    """)
    
    invalid_entries = c.fetchall()
    
    if not invalid_entries:
        print("No invalid SESSION_RESUME entries found.")
        return
    
    print(f"\nFound {len(invalid_entries)} invalid SESSION_RESUME entries:")
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
            time_diff = (datetime.fromisoformat(entry['resume_time']) - 
                        datetime.fromisoformat(entry['afgemeld_time'])).total_seconds()
            print(f"  User: {entry['user']}")
            print(f"    AFGEMELD at: {entry['afgemeld_time']}")
            print(f"    Invalid SESSION_RESUME at: {entry['resume_time']} (+{time_diff:.1f}s)")
            print(f"    Details: {entry['details']}")
            print(f"    Row ID to delete: {entry['resume_rowid']}")
    
    print("\n" + "=" * 80)
    
    # Delete the invalid entries
    rowids_to_delete = [entry['resume_rowid'] for entry in invalid_entries]
    
    print(f"\nDeleting {len(rowids_to_delete)} invalid SESSION_RESUME entries...")
    
    for rowid in rowids_to_delete:
        c.execute("DELETE FROM logs WHERE rowid = ?", (rowid,))
    
    conn.commit()
    print(f"Successfully deleted {len(rowids_to_delete)} invalid entries.")
    
    # Also check for SESSION_PAUSE entries that might need cleanup
    print("\nChecking for related SESSION_PAUSE entries...")
    c.execute("""
        SELECT COUNT(*) as count
        FROM logs sp
        JOIN logs af ON sp.project = af.project AND sp.user = af.user
        WHERE sp.event = 'SESSION_PAUSE'
        AND af.event = 'AFGEMELD'
        AND sp.timestamp > af.timestamp
    """)
    
    pause_count = c.fetchone()['count']
    if pause_count > 0:
        print(f"Note: Found {pause_count} SESSION_PAUSE entries after AFGEMELD that may also need cleanup.")
    
    # Verify the fix
    print("\nVerifying fix...")
    c.execute("""
        SELECT COUNT(*) as count
        FROM logs sr
        JOIN logs af ON sr.project = af.project AND sr.user = af.user
        WHERE sr.event = 'SESSION_RESUME'
        AND af.event = 'AFGEMELD'
        AND sr.timestamp > af.timestamp
    """)
    
    remaining = c.fetchone()['count']
    if remaining == 0:
        print("✓ All invalid SESSION_RESUME entries have been cleaned up.")
    else:
        print(f"⚠ Warning: {remaining} invalid entries still remain.")
    
    conn.close()

if __name__ == "__main__":
    fix_invalid_session_resumes()