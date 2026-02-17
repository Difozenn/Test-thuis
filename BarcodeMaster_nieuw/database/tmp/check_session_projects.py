#!/usr/bin/env python3
import sqlite3

db_path = '/mnt/c/Users/Rob_v/Desktop/PP/BarcodeMaster/database/central_logging.sqlite'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

print("=== Checking session_projects table ===")

# Count total entries
c.execute("SELECT COUNT(*) FROM session_projects")
count = c.fetchone()[0]
print(f"Total entries in session_projects: {count}")

if count > 0:
    # Show some entries
    c.execute("""
        SELECT sp.*, s.session_type, s.user, s.status 
        FROM session_projects sp
        JOIN sessions s ON sp.session_id = s.session_id
        ORDER BY sp.added_time DESC
        LIMIT 10
    """)
    print("\nRecent entries:")
    for row in c.fetchall():
        print(f"  Session: {row['session_id']}, Project: {row['project']}, Type: {row['session_type']}, User: {row['user']}")

conn.close()