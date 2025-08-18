#!/usr/bin/env python3
import sqlite3
from datetime import datetime, timedelta

db_path = '/mnt/c/Users/Rob_v/Desktop/PP/BarcodeMaster/database/central_logging.sqlite'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

print("=== Checking Recent Session Activity ===\n")

# Check recent sessions
print("1. Recent SCANNER Sessions:")
c.execute("""
    SELECT 
        session_id,
        user,
        start_time,
        end_time,
        status,
        work_duration_minutes
    FROM sessions
    WHERE session_type = 'SCANNER'
    AND datetime(start_time) >= datetime('now', '-2 hours')
    ORDER BY start_time DESC
""")

for row in c.fetchall():
    print(f"\nSession: {row['session_id']}")
    print(f"  User: {row['user']}")
    print(f"  Start: {row['start_time']}")
    print(f"  End: {row['end_time']}")
    print(f"  Status: {row['status']}")
    print(f"  Duration: {row['work_duration_minutes']} min")

print("\n2. Session Projects Links:")
c.execute("""
    SELECT 
        sp.session_id,
        sp.project,
        sp.item_count,
        sp.added_time
    FROM session_projects sp
    WHERE datetime(sp.added_time) >= datetime('now', '-2 hours')
    ORDER BY sp.added_time DESC
""")

for row in c.fetchall():
    print(f"\nSession: {row['session_id']}")
    print(f"  Project: {row['project']}")
    print(f"  Items: {row['item_count']}")
    print(f"  Added: {row['added_time']}")

print("\n3. Recent AFGEMELD Events:")
c.execute("""
    SELECT 
        timestamp,
        user,
        project,
        details,
        status
    FROM logs
    WHERE event = 'AFGEMELD'
    AND datetime(timestamp) >= datetime('now', '-2 hours')
    ORDER BY timestamp DESC
    LIMIT 10
""")

for row in c.fetchall():
    print(f"\nTime: {row['timestamp']}")
    print(f"  User: {row['user']}")
    print(f"  Project: {row['project']}")
    print(f"  Details: {row['details']}")
    print(f"  Status: {row['status']}")

print("\n4. Project Sessions Status:")
c.execute("""
    SELECT 
        project,
        start_time,
        end_time,
        total_duration_minutes,
        status
    FROM project_sessions
    WHERE datetime(start_time) >= datetime('now', '-2 hours')
    OR project IN ('MO06787_Dressing_A_deel2_(5-16)', 'MO06797_Bureaukast_(15-16)')
    ORDER BY start_time DESC
""")

for row in c.fetchall():
    print(f"\nProject: {row['project']}")
    print(f"  Start: {row['start_time']}")
    print(f"  End: {row['end_time']}")
    print(f"  Duration: {row['total_duration_minutes']} min")
    print(f"  Status: {row['status']}")

conn.close()