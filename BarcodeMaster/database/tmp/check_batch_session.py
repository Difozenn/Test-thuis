#!/usr/bin/env python3
import sqlite3
from datetime import datetime

db_path = '/mnt/c/Users/Rob_v/Desktop/PP/BarcodeMaster/database/central_logging.sqlite'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

print("=== Checking Batch Session Data ===\n")

# Check recent SCANNER sessions
print("1. Recent SCANNER Sessions:")
c.execute("""
    SELECT 
        session_id,
        user,
        start_time,
        end_time,
        status,
        work_duration_minutes,
        pause_duration_minutes,
        project
    FROM sessions
    WHERE session_type = 'SCANNER'
    AND DATE(start_time) = DATE('now')
    ORDER BY start_time DESC
    LIMIT 5
""")

sessions = c.fetchall()
for s in sessions:
    print(f"\nSession: {s['session_id']}")
    print(f"  User: {s['user']}")
    print(f"  Start: {s['start_time']}")
    print(f"  End: {s['end_time']}")
    print(f"  Status: {s['status']}")
    print(f"  Work Duration: {s['work_duration_minutes']} min")
    print(f"  Pause Duration: {s['pause_duration_minutes']} min")
    print(f"  Project field: {s['project']}")
    
    # Check linked projects
    c.execute("""
        SELECT project, item_count, added_time
        FROM session_projects
        WHERE session_id = ?
        ORDER BY added_time
    """, (s['session_id'],))
    
    linked = c.fetchall()
    if linked:
        print(f"  Linked Projects ({len(linked)}):")
        for l in linked:
            print(f"    - {l['project']}: {l['item_count']} items")
    else:
        print("  No linked projects in session_projects")

print("\n2. Project Sessions for today:")
projects = ['MO06787_Dressing_A_deel2_(5-16)', 'MO06797_Bureaukast_(15-16)']

for project in projects:
    print(f"\n{project}:")
    c.execute("""
        SELECT 
            start_time,
            end_time,
            total_duration_minutes,
            status
        FROM project_sessions
        WHERE project = ?
        AND DATE(start_time) = DATE('now')
    """, (project,))
    
    ps = c.fetchone()
    if ps:
        print(f"  Start: {ps['start_time']}")
        print(f"  End: {ps['end_time']}")
        print(f"  Total Duration: {ps['total_duration_minutes']} min")
        print(f"  Status: {ps['status']}")
    
    # Check all sessions that worked on this project
    c.execute("""
        SELECT 
            s.session_id,
            s.user,
            s.session_type,
            s.work_duration_minutes,
            sp.item_count
        FROM sessions s
        LEFT JOIN session_projects sp ON s.session_id = sp.session_id AND sp.project = ?
        WHERE (s.project = ? OR sp.project = ?)
        AND DATE(s.start_time) = DATE('now')
    """, (project, project, project))
    
    sessions = c.fetchall()
    print(f"  Sessions working on this project: {len(sessions)}")
    for s in sessions:
        if s['item_count'] is not None:
            print(f"    - {s['user']} ({s['session_type']}): {s['work_duration_minutes']} min, {s['item_count']} items")
        else:
            print(f"    - {s['user']} ({s['session_type']}): {s['work_duration_minutes']} min")

print("\n3. Checking time calculations:")
# For batch sessions, the work time should be allocated proportionally
c.execute("""
    SELECT 
        s.session_id,
        s.work_duration_minutes as total_session_minutes,
        COUNT(sp.project) as project_count,
        GROUP_CONCAT(sp.project || ':' || sp.item_count) as projects_items
    FROM sessions s
    JOIN session_projects sp ON s.session_id = sp.session_id
    WHERE s.session_type = 'SCANNER'
    AND DATE(s.start_time) = DATE('now')
    GROUP BY s.session_id
""")

batch_sessions = c.fetchall()
for bs in batch_sessions:
    print(f"\nBatch Session: {bs['session_id']}")
    print(f"  Total Duration: {bs['total_session_minutes']} min")
    print(f"  Projects: {bs['project_count']}")
    print(f"  Details: {bs['projects_items']}")
    
    # Calculate proportional allocation
    if bs['projects_items']:
        total_items = 0
        project_items = {}
        for pi in bs['projects_items'].split(','):
            proj, items = pi.split(':')
            project_items[proj] = int(items) if items else 0
            total_items += project_items[proj]
        
        if total_items > 0:
            print(f"  Proportional time allocation:")
            for proj, items in project_items.items():
                allocated_time = (items / total_items) * bs['total_session_minutes']
                print(f"    - {proj}: {allocated_time:.1f} min ({items}/{total_items} items)")

conn.close()