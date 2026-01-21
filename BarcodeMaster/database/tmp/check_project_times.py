#!/usr/bin/env python3
import sqlite3
from datetime import datetime

db_path = '/mnt/c/Users/Rob_v/Desktop/PP/BarcodeMaster/database/central_logging.sqlite'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

print("=== Checking Project Times in Database ===\n")

projects = ['MO06787_Dressing_A_deel2_(5-16)', 'MO06797_Bureaukast_(15-16)']

print("1. Project Sessions Table:")
for project in projects:
    c.execute("""
        SELECT 
            project,
            start_time,
            end_time,
            total_duration_minutes,
            status
        FROM project_sessions
        WHERE project = ?
    """, (project,))
    
    row = c.fetchone()
    if row:
        print(f"\n{row['project']}:")
        print(f"  Start: {row['start_time']}")
        print(f"  End: {row['end_time']}")
        print(f"  Total Duration: {row['total_duration_minutes']} min")
        print(f"  Status: {row['status']}")

print("\n2. SCANNER Session Details:")
c.execute("""
    SELECT 
        s.session_id,
        s.user,
        s.start_time,
        s.end_time,
        s.work_duration_minutes,
        s.pause_duration_minutes,
        GROUP_CONCAT(sp.project || ':' || sp.item_count) as projects
    FROM sessions s
    LEFT JOIN session_projects sp ON s.session_id = sp.session_id
    WHERE s.session_type = 'SCANNER'
    AND DATE(s.start_time) = DATE('2025-08-16')
    GROUP BY s.session_id
""")

for row in c.fetchall():
    print(f"\nSession: {row['session_id']}")
    print(f"  User: {row['user']}")
    print(f"  Start: {row['start_time']}")
    print(f"  End: {row['end_time']}")
    print(f"  Work Duration: {row['work_duration_minutes']} min")
    print(f"  Pause Duration: {row['pause_duration_minutes']} min")
    print(f"  Projects: {row['projects']}")

print("\n3. Logs for each project (first and last):")
for project in projects:
    c.execute("""
        SELECT 
            MIN(timestamp) as first_log,
            MAX(timestamp) as last_log,
            MIN(CASE WHEN event = 'OPEN' THEN timestamp END) as first_open,
            MAX(CASE WHEN event = 'AFGEMELD' THEN timestamp END) as last_afgemeld
        FROM logs
        WHERE project = ?
        AND DATE(timestamp) = DATE('2025-08-16')
    """, (project,))
    
    row = c.fetchone()
    if row:
        print(f"\n{project}:")
        print(f"  First log: {row['first_log']}")
        print(f"  Last log: {row['last_log']}")
        print(f"  First OPEN: {row['first_open']}")
        print(f"  Last AFGEMELD: {row['last_afgemeld']}")
        
        if row['first_log'] and row['last_log']:
            start = datetime.fromisoformat(row['first_log'])
            end = datetime.fromisoformat(row['last_log'])
            duration = (end - start).total_seconds() / 60
            print(f"  Calculated duration: {duration:.1f} min")

print("\n4. Work time allocation (what should be shown):")
c.execute("""
    SELECT 
        sp.project,
        sp.item_count,
        s.work_duration_minutes,
        s.pause_duration_minutes,
        (SELECT SUM(item_count) FROM session_projects WHERE session_id = s.session_id) as total_items
    FROM sessions s
    JOIN session_projects sp ON s.session_id = sp.session_id
    WHERE s.session_type = 'SCANNER'
    AND DATE(s.start_time) = DATE('2025-08-16')
""")

for row in c.fetchall():
    proportion = row['item_count'] / row['total_items'] if row['total_items'] > 0 else 0
    allocated_work = row['work_duration_minutes'] * proportion
    allocated_pause = (row['pause_duration_minutes'] or 0) * proportion
    total_session_time = row['work_duration_minutes'] + (row['pause_duration_minutes'] or 0)
    allocated_total = total_session_time * proportion
    
    print(f"\n{row['project']}:")
    print(f"  Items: {row['item_count']} / {row['total_items']} ({proportion:.1%})")
    print(f"  Session total time: {total_session_time:.1f} min")
    print(f"  Should get:")
    print(f"    - Project time: {allocated_total:.1f} min (proportional)")
    print(f"    - Work time: {allocated_work:.1f} min")
    print(f"    - Pause time: {allocated_pause:.1f} min")
    print(f"    - Idle time: {allocated_total - allocated_work:.1f} min")

conn.close()