#!/usr/bin/env python3
"""Check schedule data for debugging"""

import sqlite3
from datetime import datetime, date

DATABASE = 'shift_planner.db'

conn = sqlite3.connect(DATABASE)
c = conn.cursor()

print("=== SCHEDULE CHECK ===\n")

# Check schedule entries
print("Schedule entries by date:")
c.execute("""
    SELECT date, COUNT(*) as assignments 
    FROM schedule 
    WHERE date >= '2025-01-06' 
    GROUP BY date 
    ORDER BY date
""")
for row in c.fetchall():
    date_str, count = row
    # Parse date to get day of week
    dt = datetime.fromisoformat(date_str)
    day_name = dt.strftime('%A')
    print(f"{date_str} ({day_name}): {count} assignments")

print("\n" + "="*50 + "\n")

# Check if there are any jobs
print("Active jobs:")
c.execute("""
    SELECT id, name, due_date, status, priority
    FROM jobs 
    WHERE status != 'completed'
    ORDER BY due_date
""")
jobs = c.fetchall()
for job in jobs:
    print(f"Job {job[0]}: {job[1]} - Due: {job[2]} - Status: {job[3]} - Priority: {job[4]}")

print("\n" + "="*50 + "\n")

# Check people availability
print("People availability:")
c.execute("""
    SELECT p.name, a.date, a.available
    FROM people p
    LEFT JOIN availability a ON p.id = a.person_id
    WHERE a.date >= '2025-01-06' AND a.date <= '2025-01-10'
    ORDER BY a.date, p.name
""")
availability = c.fetchall()
if availability:
    current_date = None
    for name, date, available in availability:
        if date != current_date:
            print(f"\n{date}:")
            current_date = date
        status = "Available" if available else "Not Available"
        print(f"  {name}: {status}")
else:
    print("No availability records found for this week")
    
    # Check if people exist
    c.execute("SELECT COUNT(*) FROM people")
    people_count = c.fetchone()[0]
    print(f"Total people in database: {people_count}")
    
    # Default availability assumption
    print("\nNote: When no availability records exist, all people are assumed available")

print("\n" + "="*50 + "\n")

# Check detailed schedule for Wed/Thu
print("Detailed schedule for Wed (2025-01-08) and Thu (2025-01-09):")
c.execute("""
    SELECT s.date, p.name, m.name, s.start_time, s.end_time
    FROM schedule s
    JOIN people p ON s.person_id = p.id
    JOIN machines m ON s.machine_id = m.id
    WHERE s.date IN ('2025-01-08', '2025-01-09')
    ORDER BY s.date, s.start_time, p.name
""")
entries = c.fetchall()
if entries:
    for entry in entries:
        print(f"{entry[0]}: {entry[1]} on {entry[2]} ({entry[3]}-{entry[4]})")
else:
    print("No schedule entries found for these dates")

conn.close()
