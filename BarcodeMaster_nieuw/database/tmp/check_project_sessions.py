#!/usr/bin/env python3
import sqlite3
from datetime import datetime

db_path = '/mnt/c/Users/Rob_v/Desktop/PP/BarcodeMaster/database/central_logging.sqlite'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

project = 'MO07455_IT-Room_(A)_(9-19)'

print(f"=== Project: {project} ===\n")

# Check all sessions for this project
print("SESSIONS TABLE:")
c.execute("""
    SELECT session_id, user, status, session_type, 
           start_time, end_time, 
           work_duration_minutes, pause_duration_minutes,
           item_count
    FROM sessions 
    WHERE project = ? OR project LIKE ?
    ORDER BY start_time
""", (project, f'%{project}%'))

sessions = c.fetchall()
for s in sessions:
    print(f"\nSession: {s['session_id']}")
    print(f"  User: {s['user']}")
    print(f"  Type: {s['session_type']}")
    print(f"  Status: {s['status']}")
    print(f"  Start: {s['start_time']}")
    print(f"  End: {s['end_time']}")
    print(f"  Work: {s['work_duration_minutes']} min")
    print(f"  Pause: {s['pause_duration_minutes']} min")
    print(f"  Items: {s['item_count']}")

# Check logs for this project
print("\n" + "="*50)
print("LOGS TABLE (SESSION_PAUSE/RESUME/START/END):")
c.execute("""
    SELECT timestamp, event, user, details, session_id
    FROM logs 
    WHERE project = ? 
    AND event IN ('SESSION_START', 'SESSION_END', 'SESSION_PAUSE', 'SESSION_RESUME', 'AFGEMELD')
    ORDER BY timestamp
""", (project,))

for log in c.fetchall():
    time_str = log['timestamp'].split('T')[1][:8] if 'T' in log['timestamp'] else log['timestamp']
    print(f"{time_str} - {log['event']:15} - {log['user']:10} - {log['details'] or ''}")
    if log['session_id']:
        print(f"         Session: {log['session_id']}")

# Check for NESTING sessions specifically
print("\n" + "="*50)
print("ALL NESTING SESSIONS (active and completed):")
c.execute("""
    SELECT session_id, status, start_time, end_time, project
    FROM sessions 
    WHERE user = 'NESTING' 
    AND DATE(start_time) = DATE('now')
    ORDER BY start_time
""")

for s in c.fetchall():
    status_icon = "✓" if s['status'] == 'completed' else "⚫"
    end_time = s['end_time'].split('T')[1][:8] if s['end_time'] else "active"
    print(f"{status_icon} {s['session_id']} - {s['status']:10} - End: {end_time} - Project: {s['project'] or 'batch'}")

conn.close()