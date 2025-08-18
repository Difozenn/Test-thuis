#!/usr/bin/env python3
import sqlite3
from datetime import datetime

db_path = '/mnt/c/Users/Rob_v/Desktop/PP/BarcodeMaster/database/central_logging.sqlite'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Check for the specific session
session_id = 'NESTING_20250816_071642'

c.execute("""
    SELECT session_id, user, status, start_time, end_time, session_type
    FROM sessions 
    WHERE session_id = ?
""", (session_id,))

session = c.fetchone()
if session:
    print(f"Session found: {session_id}")
    print(f"  Status: {session['status']}")
    print(f"  Type: {session['session_type']}")
    print(f"  Start: {session['start_time']}")
    print(f"  End: {session['end_time']}")
else:
    print(f"Session NOT found: {session_id}")

# Check all active SCANNER sessions
print("\nAll active SCANNER sessions:")
c.execute("""
    SELECT session_id, user, status, start_time
    FROM sessions 
    WHERE session_type = 'SCANNER' AND status = 'active'
    ORDER BY start_time DESC
""")

for row in c.fetchall():
    print(f"  {row['session_id']} - {row['status']} - Started: {row['start_time']}")

conn.close()