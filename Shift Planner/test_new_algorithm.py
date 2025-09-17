#!/usr/bin/env python3
"""Test the new minimum occupation scheduling algorithm"""

import sqlite3
from datetime import datetime, timedelta
from scheduling_algorithm import SchedulingAlgorithm

DATABASE = 'shift_planner.db'

def clear_schedule():
    """Clear existing schedule"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("DELETE FROM schedule")
    conn.commit()
    print("Cleared existing schedule")
    conn.close()

def test_new_algorithm():
    """Test the new scheduling algorithm with minimum occupation"""
    
    print("=" * 80)
    print("TESTING NEW MINIMUM OCCUPATION ALGORITHM")
    print("=" * 80)
    
    # Clear existing schedule
    clear_schedule()
    
    # Create scheduler instance
    scheduler = SchedulingAlgorithm(DATABASE)
    
    # Generate schedule for next Monday
    start_date = datetime(2025, 9, 8).date()  # Monday
    end_date = datetime(2025, 9, 12).date()   # Friday
    
    print(f"\nGenerating schedule from {start_date} to {end_date}")
    print("-" * 50)
    
    # Generate assignments
    assignments = scheduler.generate_schedule(start_date, end_date)
    
    print(f"\nGenerated {len(assignments)} assignments")
    
    # Save to database
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    for assignment in assignments:
        c.execute('''INSERT INTO schedule 
                    (date, machine_id, person_id, job_id, start_time, end_time)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                 (assignment['date'], assignment['machine_id'], 
                  assignment['person_id'], assignment['job_id'],
                  assignment['start_time'], assignment['end_time']))
    
    conn.commit()
    print(f"Saved {len(assignments)} assignments to database")
    
    # Analyze the results
    print("\n" + "=" * 80)
    print("ALGORITHM RESULTS:")
    print("=" * 80)
    
    c.execute("""SELECT m.name, COUNT(DISTINCT p.id) as operator_count,
                        GROUP_CONCAT(DISTINCT p.name) as operators
                 FROM schedule s
                 JOIN machines m ON s.machine_id = m.id
                 JOIN people p ON s.person_id = p.id
                 WHERE s.date = ?
                 GROUP BY m.id, m.name""", (start_date.isoformat(),))
    
    results = c.fetchall()
    
    print("\nMachine Assignments for", start_date)
    print("-" * 50)
    for machine, count, operators in results:
        print(f"{machine:15} : {count} operators - {operators}")
    
    # Check detailed assignments
    print("\nDetailed Schedule:")
    print("-" * 50)
    c.execute("""SELECT s.date, m.name, p.name, j.project_name, s.start_time, s.end_time
                 FROM schedule s
                 JOIN machines m ON s.machine_id = m.id
                 JOIN people p ON s.person_id = p.id
                 LEFT JOIN jobs j ON s.job_id = j.id
                 WHERE s.date = ?
                 ORDER BY m.name, s.start_time""", (start_date.isoformat(),))
    
    for row in c.fetchall():
        print(f"{row[0]} | {row[1]:15} | {row[2]:15} | {row[3]:20} | {row[4]}-{row[5]}")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("EXPECTED BEHAVIOR:")
    print("=" * 80)
    print("""
With minimum occupation strategy:
- Phase 1: Assigns 1 operator to each machine that has work
  - Cel Holzher gets 1 operator (for maatwerk job)
  - Tekenbureel gets 1 operator (for Tekenwerk job)
  
- Phase 2: Assigns additional operators up to max capacity
  - Cel Holzher can get up to 3 more (max=4 total)
  - Tekenbureel can get up to 2 more (max=3 total)
  
This should result in more balanced distribution like 2-2 or 3-1
instead of the previous 3-1 that happened due to greedy assignment.
""")

if __name__ == '__main__':
    test_new_algorithm()