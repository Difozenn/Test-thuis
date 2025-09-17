#!/usr/bin/env python3
"""Debug the scheduling algorithm to understand assignments"""

import sqlite3

DATABASE = 'shift_planner.db'

def debug_skills():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    print("=" * 80)
    print("SKILL ANALYSIS FOR SCHEDULING")
    print("=" * 80)
    
    # Get all people and their skills
    c.execute("""SELECT p.id, p.name FROM people p ORDER BY p.name""")
    people = c.fetchall()
    
    for person_id, person_name in people:
        print(f"\n{person_name} (ID: {person_id}):")
        
        c.execute("""SELECT m.name, s.skill_level
                     FROM skills s
                     JOIN machines m ON s.machine_id = m.id
                     WHERE s.person_id = ?
                     ORDER BY s.skill_level DESC""", (person_id,))
        
        skills = c.fetchall()
        if skills:
            for machine, level in skills:
                print(f"  - {machine:15} : Level {level}")
        else:
            print("  - No skills recorded")
    
    print("\n" + "=" * 80)
    print("CRITICAL INSIGHT:")
    print("=" * 80)
    
    # Check who can work on each machine
    machines_of_interest = ['Cel Holzher', 'Tekenbureel']
    
    for machine_name in machines_of_interest:
        c.execute("""SELECT p.name, s.skill_level
                     FROM skills s
                     JOIN people p ON s.person_id = p.id
                     JOIN machines m ON s.machine_id = m.id
                     WHERE m.name = ?
                     ORDER BY s.skill_level DESC""", (machine_name,))
        
        operators = c.fetchall()
        print(f"\n{machine_name} - Can be operated by:")
        for op_name, level in operators:
            print(f"  - {op_name:15} (Level {level})")
    
    # Find multi-skilled workers
    print("\n" + "=" * 80)
    print("MULTI-SKILLED WORKERS (Can work multiple machines):")
    print("=" * 80)
    
    c.execute("""SELECT p.name, COUNT(DISTINCT s.machine_id) as num_machines,
                        GROUP_CONCAT(m.name || ' (L' || s.skill_level || ')') as machines
                 FROM people p
                 JOIN skills s ON p.id = s.person_id
                 JOIN machines m ON s.machine_id = m.id
                 GROUP BY p.id, p.name
                 HAVING num_machines > 1
                 ORDER BY num_machines DESC""")
    
    multi_skilled = c.fetchall()
    for name, count, machines in multi_skilled:
        print(f"{name:15} - {count} machines: {machines}")
    
    print("\n" + "=" * 80)
    print("THE PROBLEM:")
    print("=" * 80)
    print("""
Dennis VW is the ONLY person who can work BOTH Cel Holzher AND Tekenbureel.

Current algorithm behavior:
1. Phase 1 assigns Dennis VW to Cel Holzher (first job processed)
2. Phase 1 then tries to assign someone to Tekenbureel, finds only Jarne available
3. Phase 2 adds more people to machines

The issue: Dennis VW should be reserved for where he's uniquely needed!

SOLUTION: The algorithm needs to be smarter about multi-skilled workers:
- Identify workers with unique or rare skill combinations
- Reserve them for machines where they're most critically needed
- Assign single-skilled workers first where possible
""")
    
    conn.close()

if __name__ == '__main__':
    debug_skills()