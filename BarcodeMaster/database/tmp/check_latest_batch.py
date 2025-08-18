#!/usr/bin/env python3
import sqlite3
from datetime import datetime

db_path = '/mnt/c/Users/Rob_v/Desktop/PP/BarcodeMaster/database/central_logging.sqlite'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

print("=== Checking Latest Batch Session ===\n")

# Find the latest batch session
c.execute("""
    SELECT 
        s.session_id,
        s.user,
        s.start_time,
        s.end_time,
        s.work_duration_minutes,
        s.pause_duration_minutes,
        s.status,
        GROUP_CONCAT(sp.project || ':' || sp.item_count) as projects
    FROM sessions s
    LEFT JOIN session_projects sp ON s.session_id = sp.session_id
    WHERE s.session_type = 'SCANNER'
    AND DATE(s.start_time) = DATE('2025-08-16')
    AND TIME(s.start_time) >= '19:00:00'
    GROUP BY s.session_id
    ORDER BY s.start_time DESC
""")

session = c.fetchone()
if session:
    print(f"Session: {session['session_id']}")
    print(f"  Status: {session['status']}")
    print(f"  Start: {session['start_time']}")
    print(f"  End: {session['end_time']}")
    print(f"  Work Duration: {session['work_duration_minutes']} min")
    print(f"  Projects: {session['projects']}")
    
    # Calculate total session time
    if session['end_time']:
        start = datetime.fromisoformat(session['start_time'])
        end = datetime.fromisoformat(session['end_time'])
        actual_duration = (end - start).total_seconds() / 60
        print(f"  Actual Duration: {actual_duration:.1f} min")

print("\n=== Project Sessions Data ===\n")

# Check project_sessions for the batch projects
c.execute("""
    SELECT 
        project,
        start_time,
        end_time,
        total_duration_minutes,
        status
    FROM project_sessions
    WHERE project = 'MO06787_Dressing_A_deel2_(5-16)'
    ORDER BY start_time DESC
    LIMIT 2
""")

for row in c.fetchall():
    print(f"Project: {row['project']}")
    print(f"  Start: {row['start_time']}")
    print(f"  End: {row['end_time']}")
    print(f"  Duration: {row['total_duration_minutes']} min")
    print(f"  Status: {row['status']}")
    
    if row['start_time'] and row['end_time']:
        start = datetime.fromisoformat(row['start_time'])
        end = datetime.fromisoformat(row['end_time'])
        calculated = (end - start).total_seconds() / 60
        print(f"  Calculated from timestamps: {calculated:.1f} min")
    print()

print("=== What Should Be Correct ===\n")

# Calculate what the proportional time should be
if session and session['projects']:
    projects_data = {}
    total_items = 0
    
    for project_info in session['projects'].split(','):
        project, items = project_info.split(':')
        projects_data[project] = int(items)
        total_items += int(items)
    
    total_time = session['work_duration_minutes'] or 0
    if session['pause_duration_minutes']:
        total_time += session['pause_duration_minutes']
    
    print(f"Total batch time: {total_time:.1f} min")
    print(f"Total items: {total_items}")
    
    for project, items in projects_data.items():
        proportion = items / total_items if total_items > 0 else 0
        proportional_time = total_time * proportion
        print(f"\n{project}:")
        print(f"  Items: {items} ({proportion:.1%})")
        print(f"  Should get: {proportional_time:.1f} min project time")

conn.close()