#!/usr/bin/env python3
"""Test the minimum operators configuration"""

import sqlite3
from datetime import datetime
from scheduling_algorithm import SchedulingAlgorithm

DATABASE = 'shift_planner.db'

def set_minimum_operators():
    """Configure minimum operators for testing"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    print("=" * 80)
    print("CONFIGURING MINIMUM OPERATORS")
    print("=" * 80)
    
    # Set Tekenbureel to require minimum 2 operators when it has work
    c.execute("UPDATE machines SET min_operators = 2 WHERE name = 'Tekenbureel'")
    
    # Keep Cel Holzher at minimum 1
    c.execute("UPDATE machines SET min_operators = 1 WHERE name = 'Cel Holzher'")
    
    conn.commit()
    
    # Show updated configuration
    c.execute("SELECT name, min_operators, max_operators FROM machines WHERE name IN ('Cel Holzher', 'Tekenbureel')")
    for name, min_op, max_op in c.fetchall():
        print(f"{name:15} - Min: {min_op}, Max: {max_op}")
    
    conn.close()

def test_with_minimum():
    """Test scheduling with minimum operators"""
    
    print("\n" + "=" * 80)
    print("TESTING WITH MINIMUM OPERATORS")
    print("=" * 80)
    
    # Clear existing schedule
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("DELETE FROM schedule")
    conn.commit()
    
    # Create scheduler and generate schedule
    scheduler = SchedulingAlgorithm(DATABASE)
    start_date = datetime(2025, 9, 8).date()
    end_date = datetime(2025, 9, 8).date()  # Just Monday for testing
    
    print(f"\nGenerating schedule for {start_date}")
    assignments = scheduler.generate_schedule(start_date, end_date)
    
    # Save assignments
    for assignment in assignments:
        c.execute('''INSERT INTO schedule 
                    (date, machine_id, person_id, job_id, start_time, end_time)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                 (assignment['date'], assignment['machine_id'], 
                  assignment['person_id'], assignment['job_id'],
                  assignment['start_time'], assignment['end_time']))
    
    conn.commit()
    
    # Analyze results
    print("\n" + "=" * 80)
    print("RESULTS WITH MINIMUM OPERATORS:")
    print("=" * 80)
    
    c.execute("""SELECT m.name, COUNT(DISTINCT p.id) as operator_count,
                        GROUP_CONCAT(DISTINCT p.name) as operators
                 FROM schedule s
                 JOIN machines m ON s.machine_id = m.id
                 JOIN people p ON s.person_id = p.id
                 WHERE s.date = ?
                 GROUP BY m.id, m.name""", (start_date.isoformat(),))
    
    for machine, count, operators in c.fetchall():
        print(f"{machine:15} : {count} operators - {operators}")
    
    print("\n" + "=" * 80)
    print("EXPECTED BEHAVIOR:")
    print("=" * 80)
    print("""
With minimum operators configured:
- Tekenbureel has min_operators = 2, so it should get AT LEAST 2 operators
- Cel Holzher has min_operators = 1, so it should get AT LEAST 1 operator

Expected distribution:
- Tekenbureel: 2 operators (Dennis VW and Jarne) - meeting minimum
- Cel Holzher: 2 operators (Rob VL and Glen) - remaining available

This gives us a balanced 2-2 distribution!
""")
    
    conn.close()

def test_high_priority_override():
    """Test that high priority jobs can override minimum operators"""
    
    print("\n" + "=" * 80)
    print("TESTING HIGH PRIORITY OVERRIDE")
    print("=" * 80)
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Make the maatwerk job high priority
    c.execute("UPDATE jobs SET priority = 1 WHERE project_name = 'maatwerk'")
    conn.commit()
    
    # Clear and regenerate schedule
    c.execute("DELETE FROM schedule")
    conn.commit()
    
    scheduler = SchedulingAlgorithm(DATABASE)
    start_date = datetime(2025, 9, 8).date()
    end_date = datetime(2025, 9, 8).date()
    
    print(f"\nGenerating schedule with HIGH PRIORITY job")
    assignments = scheduler.generate_schedule(start_date, end_date)
    
    # Save assignments
    for assignment in assignments:
        c.execute('''INSERT INTO schedule 
                    (date, machine_id, person_id, job_id, start_time, end_time)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                 (assignment['date'], assignment['machine_id'], 
                  assignment['person_id'], assignment['job_id'],
                  assignment['start_time'], assignment['end_time']))
    
    conn.commit()
    
    # Analyze results
    print("\nResults with HIGH PRIORITY:")
    c.execute("""SELECT m.name, COUNT(DISTINCT p.id) as operator_count,
                        GROUP_CONCAT(DISTINCT p.name) as operators
                 FROM schedule s
                 JOIN machines m ON s.machine_id = m.id
                 JOIN people p ON s.person_id = p.id
                 WHERE s.date = ?
                 GROUP BY m.id, m.name""", (start_date.isoformat(),))
    
    for machine, count, operators in c.fetchall():
        print(f"{machine:15} : {count} operators - {operators}")
    
    print("""
With high priority override:
- High priority jobs can pull operators away from minimum requirements
- This allows critical work to get maximum resources
""")
    
    # Reset priority
    c.execute("UPDATE jobs SET priority = 0 WHERE project_name = 'maatwerk'")
    conn.commit()
    conn.close()

if __name__ == '__main__':
    set_minimum_operators()
    test_with_minimum()
    test_high_priority_override()