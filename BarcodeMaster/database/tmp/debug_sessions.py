#!/usr/bin/env python3
import sqlite3
from datetime import datetime, timedelta

db_path = '/mnt/c/Users/Rob_v/Desktop/PP/BarcodeMaster/database/central_logging.sqlite'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

print("=== Recent SCANNER Sessions ===\n")

# Show recent SCANNER sessions
c.execute("""
    SELECT session_id, user, project, item_count, status, 
           datetime(start_time) as start_time,
           datetime(end_time) as end_time
    FROM sessions 
    WHERE session_type = 'SCANNER'
    AND datetime(start_time) >= datetime('now', '-1 day')
    ORDER BY start_time DESC
""")

for row in c.fetchall():
    print(f"Session: {row['session_id']}")
    print(f"  User: {row['user']}")
    print(f"  Project: {row['project']}")
    print(f"  Items: {row['item_count']}")
    print(f"  Status: {row['status']}")
    print(f"  Start: {row['start_time']}")
    print(f"  End: {row['end_time']}")
    print()

print("=== Session Projects Links ===\n")
c.execute("""
    SELECT COUNT(*) as count FROM session_projects
""")
count = c.fetchone()['count']
print(f"Total links: {count}")

if count > 0:
    c.execute("""
        SELECT * FROM session_projects
        ORDER BY added_time DESC
        LIMIT 10
    """)
    for row in c.fetchall():
        print(f"  Session: {row['session_id']}, Project: {row['project']}")

conn.close()