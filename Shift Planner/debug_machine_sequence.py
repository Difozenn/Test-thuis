#!/usr/bin/env python3
"""Debug why some machines in sequences aren't getting operators"""

import sqlite3

DATABASE = 'shift_planner.db'

def debug_sequence():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    print("=" * 80)
    print("DEBUGGING MACHINE SEQUENCE SCHEDULING")
    print("=" * 80)
    
    # Check job sequences
    print("\n1. JOB SEQUENCES:")
    print("-" * 40)
    c.execute("SELECT id, project_name, machine_sequence, priority FROM jobs WHERE status != 'completed'")
    for job_id, name, sequence, priority in c.fetchall():
        print(f"Job: {name}")
        print(f"  Sequence: {sequence}")
        print(f"  Priority: {priority}")
        if sequence:
            machines = [m.strip() for m in sequence.split(',')]
            print(f"  Machines needed ({len(machines)}): {', '.join(machines)}")
    
    # Check people skills for each machine
    print("\n2. PEOPLE SKILLS BY MACHINE:")
    print("-" * 40)
    c.execute("SELECT id, name FROM machines")
    machines = c.fetchall()
    
    for machine_id, machine_name in machines:
        c.execute("""SELECT p.name, s.skill_level
                     FROM skills s
                     JOIN people p ON s.person_id = p.id
                     WHERE s.machine_id = ?
                     ORDER BY s.skill_level DESC""", (machine_id,))
        
        skilled_people = c.fetchall()
        print(f"\n{machine_name}:")
        if skilled_people:
            for person, level in skilled_people:
                print(f"  - {person:15} Level {level}")
        else:
            print("  - NO SKILLED OPERATORS!")
    
    # Check current schedule
    print("\n3. CURRENT SCHEDULE ASSIGNMENTS:")
    print("-" * 40)
    c.execute("""SELECT DISTINCT m.name, COUNT(DISTINCT s.person_id) as count
                 FROM schedule s
                 JOIN machines m ON s.machine_id = m.id
                 WHERE s.date = '2025-09-08'
                 GROUP BY m.id, m.name""")
    
    scheduled = c.fetchall()
    if scheduled:
        for machine, count in scheduled:
            print(f"{machine:15} : {count} operators assigned")
    else:
        print("No schedule found")
    
    # Identify the problem
    print("\n4. PROBLEM ANALYSIS:")
    print("-" * 40)
    
    # Get maatwerk job sequence
    c.execute("SELECT machine_sequence FROM jobs WHERE project_name = 'maatwerk'")
    sequence = c.fetchone()[0]
    machines_needed = [m.strip() for m in sequence.split(',')]
    
    print(f"Maatwerk needs: {', '.join(machines_needed)}")
    
    # Check which machines have no operators
    unassigned_machines = []
    for machine in machines_needed:
        c.execute("""SELECT COUNT(*) FROM schedule s
                     JOIN machines m ON s.machine_id = m.id
                     WHERE m.name = ? AND s.date = '2025-09-08'""", (machine,))
        count = c.fetchone()[0]
        if count == 0:
            unassigned_machines.append(machine)
    
    if unassigned_machines:
        print(f"\nMachines NOT scheduled: {', '.join(unassigned_machines)}")
        
        # Check if people have skills for these
        for machine in unassigned_machines:
            c.execute("""SELECT COUNT(*) FROM skills s
                         JOIN machines m ON s.machine_id = m.id
                         WHERE m.name = ?""", (machine,))
            skilled_count = c.fetchone()[0]
            print(f"  {machine}: {skilled_count} people have skills")
    
    print("\n5. ROOT CAUSE:")
    print("-" * 40)
    print("""
The algorithm is only assigning operators to the FIRST machine in each job's sequence!

Issue: The current logic assigns all operators to work on the first machine,
but doesn't handle the subsequent machines in the sequence.

For the maatwerk job:
- Sequence: Cel Holzher → Boere → Radri → Spuitband
- Only Cel Holzher is getting operators
- Boere, Radri, Spuitband are ignored

This is because the algorithm treats the entire sequence as happening 
simultaneously rather than sequentially through the day/week.
""")
    
    conn.close()

if __name__ == '__main__':
    debug_sequence()