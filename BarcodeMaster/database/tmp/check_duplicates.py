#!/usr/bin/env python3
import sqlite3
from datetime import datetime

db_path = '/mnt/c/Users/Rob_v/Desktop/PP/BarcodeMaster/database/central_logging.sqlite'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

print("=== Checking for Duplicate Logs ===\n")

# Check logs for MO06797_Bureaukast
project = 'MO06797_Bureaukast_(15-16)'
print(f"Logs for {project}:")

c.execute("""
    SELECT 
        id,
        timestamp,
        event,
        user,
        status,
        item_count
    FROM logs
    WHERE project = ?
    ORDER BY timestamp DESC
    LIMIT 20
""", (project,))

logs = c.fetchall()
for log in logs:
    time_str = datetime.fromisoformat(log['timestamp']).strftime('%H:%M:%S')
    status_str = log['status'] or 'N/A'
    print(f"  ID:{log['id']} {time_str} {log['event']:10} {log['user']:15} {status_str:10} Items:{log['item_count']}")

print(f"\nTotal logs for this project: {len(logs)}")

print("\n=== Checking Sessions ===\n")

# Check all SCANNER sessions from today
c.execute("""
    SELECT 
        session_id,
        user,
        start_time,
        end_time,
        status
    FROM sessions
    WHERE session_type = 'SCANNER'
    AND DATE(start_time) = DATE('now')
    ORDER BY start_time DESC
""")

sessions = c.fetchall()
print(f"SCANNER sessions today: {len(sessions)}")
for session in sessions:
    start = datetime.fromisoformat(session['start_time']).strftime('%H:%M:%S')
    end = datetime.fromisoformat(session['end_time']).strftime('%H:%M:%S') if session['end_time'] else 'ongoing'
    print(f"  {session['session_id']}: {start} - {end} ({session['status']})")

print("\n=== Session Projects Links ===\n")

# Check session_projects for duplicates
c.execute("""
    SELECT 
        sp.session_id,
        sp.project,
        sp.item_count,
        sp.added_time,
        s.start_time as session_start
    FROM session_projects sp
    JOIN sessions s ON sp.session_id = s.session_id
    WHERE sp.project = ?
    ORDER BY sp.added_time DESC
""", (project,))

links = c.fetchall()
print(f"Session links for {project}: {len(links)}")
for link in links:
    added = datetime.fromisoformat(link['added_time']).strftime('%H:%M:%S')
    session_start = datetime.fromisoformat(link['session_start']).strftime('%H:%M:%S')
    print(f"  Session {link['session_id'][:20]}... (started {session_start})")
    print(f"    Added at: {added}, Items: {link['item_count']}")

print("\n=== Checking for Actual Duplicates ===\n")

# Check for duplicate OPEN events for same user/project/timestamp
c.execute("""
    SELECT 
        event,
        user,
        project,
        timestamp,
        COUNT(*) as count
    FROM logs
    WHERE DATE(timestamp) = DATE('now')
    GROUP BY event, user, project, timestamp
    HAVING COUNT(*) > 1
""")

duplicates = c.fetchall()
if duplicates:
    print("Found duplicate entries:")
    for dup in duplicates:
        print(f"  {dup['event']} - {dup['user']} - {dup['project']} - {dup['timestamp']}: {dup['count']} copies")
else:
    print("No exact duplicates found (same event/user/project/timestamp)")

conn.close()