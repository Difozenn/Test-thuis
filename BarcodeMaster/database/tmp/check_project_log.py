#!/usr/bin/env python3
import sqlite3

db_path = '/mnt/c/Users/Rob_v/Desktop/PP/BarcodeMaster/database/central_logging.sqlite'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

project = 'MO07455_IT-Room_(A)_(9-19)'

print("PROJECT_LOG TABLE:")
c.execute("""
    SELECT timestamp, event, user, item_count
    FROM project_log 
    WHERE project = ?
    ORDER BY timestamp
""", (project,))

for row in c.fetchall():
    time_str = row['timestamp'].split('T')[1][:8] if 'T' in row['timestamp'] else row['timestamp']
    print(f"{time_str} - {row['event']:10} - {row['user']:10} - Items: {row['item_count']}")

print("\n" + "="*50)
print("LOGS TABLE (ALL EVENTS):")
c.execute("""
    SELECT timestamp, event, user, status, item_count, details
    FROM logs 
    WHERE project = ?
    ORDER BY timestamp
""", (project,))

for row in c.fetchall():
    time_str = row['timestamp'].split('T')[1][:8] if 'T' in row['timestamp'] else row['timestamp']
    status = row['status'] or 'N/A'
    print(f"{time_str} - {row['event']:15} - {row['user']:10} - {status:8} - Items: {row['item_count']} - {row['details'] or ''}")

conn.close()