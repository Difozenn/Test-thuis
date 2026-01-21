#!/usr/bin/env python3
import sqlite3

db_path = '/mnt/c/Users/Rob_v/Desktop/PP/BarcodeMaster/database/central_logging.sqlite'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

print("=== Checking Project Sessions for MO06797_Bureaukast ===\n")

# Check all project_sessions entries
c.execute("""
    SELECT 
        project,
        start_time,
        end_time,
        total_duration_minutes,
        status
    FROM project_sessions
    WHERE project LIKE '%MO06797%'
    ORDER BY start_time DESC
""")

for row in c.fetchall():
    print(f"Project: {row['project']}")
    print(f"  Start: {row['start_time']}")
    print(f"  End: {row['end_time']}")
    print(f"  Duration: {row['total_duration_minutes']} min")
    print(f"  Status: {row['status']}")
    print()

print("=== Batch Sessions with MO06797 ===\n")

# Check which sessions included this project
c.execute("""
    SELECT 
        s.session_id,
        s.start_time,
        s.end_time,
        s.work_duration_minutes,
        sp.item_count,
        (SELECT SUM(item_count) FROM session_projects WHERE session_id = s.session_id) as total_items
    FROM sessions s
    JOIN session_projects sp ON s.session_id = sp.session_id
    WHERE sp.project LIKE '%MO06797%'
    ORDER BY s.start_time DESC
""")

for row in c.fetchall():
    proportion = row['item_count'] / row['total_items'] if row['total_items'] else 0
    allocated_time = (row['work_duration_minutes'] or 0) * proportion
    
    print(f"Session: {row['session_id']}")
    print(f"  Start: {row['start_time']}")
    print(f"  End: {row['end_time']}")
    print(f"  Total Duration: {row['work_duration_minutes']} min")
    print(f"  Items: {row['item_count']} / {row['total_items']} ({proportion:.1%})")
    print(f"  Allocated Time: {allocated_time:.1f} min")
    print()

print("=== Latest API Query Test ===\n")

# Test the API query
project = 'MO06797_Bureaukast_(15-16)'
c.execute("""
    SELECT total_duration_minutes 
    FROM project_sessions 
    WHERE project = ?
    ORDER BY start_time DESC
    LIMIT 1
""", (project,))

result = c.fetchone()
if result:
    print(f"Latest project_sessions duration for {project}: {result['total_duration_minutes']} min")
else:
    print(f"No project_sessions found for {project}")

conn.close()