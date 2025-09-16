import sqlite3
from datetime import datetime

# Connect to database
conn = sqlite3.connect('central_logging.sqlite')
c = conn.cursor()

print("Analyzing double pause issue for OPUS on MO08383_TV-wand_(1-1)")
print("=" * 80)

# Get all events for OPUS on Sept 11-12
c.execute("""
    SELECT timestamp, event, details, session_id
    FROM logs 
    WHERE project = 'MO08383_TV-wand_(1-1)' 
    AND user = 'OPUS'
    AND timestamp BETWEEN '2025-09-11' AND '2025-09-13'
    ORDER BY timestamp
""")

events = c.fetchall()

print("\nAll OPUS events (Sept 11-12):")
print("-" * 80)
for event in events:
    print(f"{event[0]} | {event[1]:20} | {event[3] or 'None':30} | {event[2] or ''}")

# Check if there are any sessions that might have triggered the pause
print("\n\nChecking sessions for OPUS on Sept 11-12:")
print("-" * 80)
c.execute("""
    SELECT session_id, session_type, project, start_time, end_time, status, pause_start
    FROM sessions
    WHERE user = 'OPUS'
    AND (
        (start_time BETWEEN '2025-09-11' AND '2025-09-13')
        OR (end_time BETWEEN '2025-09-11' AND '2025-09-13')
    )
    ORDER BY start_time
""")

sessions = c.fetchall()
for session in sessions:
    print(f"Session: {session[0]}")
    print(f"  Type: {session[1]}")
    print(f"  Project: {session[2]}")
    print(f"  Start: {session[3]}")
    print(f"  End: {session[4] or 'Active'}")
    print(f"  Status: {session[5]}")
    print(f"  Pause Start: {session[6] or 'None'}")
    print()

# Check if there are any events from the same time that might indicate what triggered the pause
print("\nAll system events around the double pause time (08:49:00 - 08:50:00):")
print("-" * 80)
c.execute("""
    SELECT timestamp, user, event, project, details
    FROM logs
    WHERE timestamp BETWEEN '2025-09-12T08:49:00' AND '2025-09-12T08:50:00'
    ORDER BY timestamp
""")

for event in c.fetchall():
    print(f"{event[0]} | {event[1]:10} | {event[2]:20} | {event[3] or 'None':30} | {event[4] or ''}")

conn.close()