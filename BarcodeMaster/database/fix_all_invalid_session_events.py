#!/usr/bin/env python3
"""
Comprehensive script to clean up all invalid session-related entries that occur after AFGEMELD events.
This includes PROJECT_START, SESSION_RESUME, and SESSION_PAUSE entries.
"""

import sqlite3
from datetime import datetime

def fix_all_invalid_session_events():
    """Remove all invalid session events that occur after AFGEMELD for the same user/project"""
    
    conn = sqlite3.connect('central_logging.sqlite')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    print("=" * 80)
    print("COMPREHENSIVE CLEANUP OF INVALID SESSION EVENTS AFTER AFGEMELD")
    print("=" * 80)
    
    total_deleted = 0
    
    # Define the event types to check
    invalid_event_types = ['PROJECT_START', 'SESSION_RESUME', 'SESSION_PAUSE']
    
    for event_type in invalid_event_types:
        print(f"\n{'-' * 60}")
        print(f"Checking for invalid {event_type} entries...")
        print(f"{'-' * 60}")
        
        # Find all invalid entries of this type
        c.execute(f"""
            SELECT 
                e.rowid as event_rowid,
                e.id as event_id,
                e.timestamp as event_time,
                e.project,
                e.user,
                af.timestamp as afgemeld_time,
                e.details,
                e.event
            FROM logs e
            JOIN logs af ON e.project = af.project AND e.user = af.user
            WHERE e.event = ?
            AND af.event = 'AFGEMELD'
            AND e.timestamp > af.timestamp
            ORDER BY e.project, e.user, e.timestamp
        """, (event_type,))
        
        invalid_entries = c.fetchall()
        
        if not invalid_entries:
            print(f"✓ No invalid {event_type} entries found.")
            continue
        
        print(f"⚠ Found {len(invalid_entries)} invalid {event_type} entries:")
        
        # Group by project for better display
        by_project = {}
        for entry in invalid_entries:
            project = entry['project']
            if project not in by_project:
                by_project[project] = []
            by_project[project].append(entry)
        
        # Display findings
        for project, entries in by_project.items():
            print(f"\n  Project: {project}")
            for entry in entries:
                time_diff = (datetime.fromisoformat(entry['event_time']) - 
                            datetime.fromisoformat(entry['afgemeld_time'])).total_seconds()
                print(f"    User: {entry['user']}")
                print(f"      AFGEMELD at: {entry['afgemeld_time']}")
                print(f"      Invalid {event_type} at: {entry['event_time']} (+{time_diff:.1f}s)")
                if entry['details']:
                    print(f"      Details: {entry['details'][:50]}...")
                print(f"      ID to delete: {entry['event_id']}")
        
        # Delete the invalid entries
        rowids_to_delete = [entry['event_rowid'] for entry in invalid_entries]
        
        print(f"\n  Deleting {len(rowids_to_delete)} invalid {event_type} entries...")
        
        for rowid in rowids_to_delete:
            c.execute("DELETE FROM logs WHERE rowid = ?", (rowid,))
        
        conn.commit()
        print(f"  ✓ Successfully deleted {len(rowids_to_delete)} {event_type} entries.")
        total_deleted += len(rowids_to_delete)
    
    print("\n" + "=" * 80)
    print(f"SUMMARY: Deleted {total_deleted} total invalid entries")
    print("=" * 80)
    
    # Final verification
    print("\nPerforming final verification...")
    
    for event_type in invalid_event_types:
        c.execute(f"""
            SELECT COUNT(*) as count
            FROM logs e
            JOIN logs af ON e.project = af.project AND e.user = af.user
            WHERE e.event = ?
            AND af.event = 'AFGEMELD'
            AND e.timestamp > af.timestamp
        """, (event_type,))
        
        remaining = c.fetchone()['count']
        if remaining == 0:
            print(f"✓ All invalid {event_type} entries have been cleaned up.")
        else:
            print(f"⚠ Warning: {remaining} invalid {event_type} entries still remain.")
    
    conn.close()
    print("\nCleanup complete!")

if __name__ == "__main__":
    fix_all_invalid_session_events()