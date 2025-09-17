#!/usr/bin/env python3
"""Analyze why the scheduling algorithm made specific assignments"""

import sqlite3
from datetime import datetime

DATABASE = 'shift_planner.db'

def analyze_schedule():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    print("=" * 80)
    print("SCHEDULING ALGORITHM ANALYSIS")
    print("=" * 80)
    
    # 1. Check machine configurations
    print("\n1. MACHINE CONFIGURATIONS:")
    print("-" * 40)
    c.execute("SELECT * FROM machines ORDER BY id")
    machines = c.fetchall()
    machine_dict = {}
    for machine in machines:
        machine_dict[machine[0]] = machine[1]
        print(f"   Machine ID {machine[0]}: {machine[1]}")
        print(f"      - Max Operators: {machine[2]}")
        print(f"      - Base Throughput: {machine[3]}")
    
    # 2. Check jobs that were scheduled
    print("\n2. JOBS IN THE SYSTEM:")
    print("-" * 40)
    c.execute("""SELECT id, project_name, quantity, due_date, priority, 
                        precision_required, machine_sequence, estimated_hours, status
                 FROM jobs ORDER BY priority DESC, due_date""")
    jobs = c.fetchall()
    for job in jobs:
        print(f"   Job ID {job[0]}: {job[1]}")
        print(f"      - Quantity: {job[2]}")
        print(f"      - Due Date: {job[3]}")
        print(f"      - Priority: {job[4]} {'(HIGH)' if job[4] > 0 else '(NORMAL)'}")
        print(f"      - Precision Required: {bool(job[5])}")
        print(f"      - Machine Sequence: {job[6]}")
        print(f"      - Estimated Hours: {job[7]}")
        print(f"      - Status: {job[8]}")
    
    # 3. Check people skills
    print("\n3. PEOPLE SKILLS FOR RELEVANT MACHINES:")
    print("-" * 40)
    c.execute("""SELECT p.name, m.name, s.skill_level 
                 FROM skills s
                 JOIN people p ON s.person_id = p.id
                 JOIN machines m ON s.machine_id = m.id
                 WHERE m.name IN ('Cel Holzher', 'Tekenbureel')
                 ORDER BY m.name, s.skill_level DESC""")
    skills = c.fetchall()
    
    cel_holzher_operators = []
    tekenbureel_operators = []
    
    for skill in skills:
        print(f"   {skill[0]:15} - {skill[1]:15} - Level {skill[2]}")
        if skill[1] == 'Cel Holzher':
            cel_holzher_operators.append((skill[0], skill[2]))
        else:
            tekenbureel_operators.append((skill[0], skill[2]))
    
    # 4. Check actual schedule assignments
    print("\n4. ACTUAL SCHEDULE ASSIGNMENTS:")
    print("-" * 40)
    c.execute("""SELECT s.date, m.name, p.name, j.project_name, s.start_time, s.end_time
                 FROM schedule s
                 JOIN machines m ON s.machine_id = m.id
                 JOIN people p ON s.person_id = p.id
                 LEFT JOIN jobs j ON s.job_id = j.id
                 ORDER BY s.date, m.name, s.start_time""")
    schedules = c.fetchall()
    
    assignments_by_machine = {}
    for schedule in schedules:
        machine_name = schedule[1]
        if machine_name not in assignments_by_machine:
            assignments_by_machine[machine_name] = []
        assignments_by_machine[machine_name].append(schedule)
        print(f"   {schedule[0]} | {schedule[1]:15} | {schedule[2]:15} | {schedule[3]:20} | {schedule[4]}-{schedule[5]}")
    
    # 5. Analysis of the algorithm's decision
    print("\n5. ALGORITHM DECISION ANALYSIS:")
    print("-" * 40)
    print("\nWhy 3 people on Cel Holzher and 1 on Tekenbureel?")
    print("-" * 50)
    
    # Find which jobs required which machines
    cel_jobs = []
    tek_jobs = []
    for job in jobs:
        if 'Cel Holzher' in job[6]:
            cel_jobs.append(job[1])
        if 'Tekenbureel' in job[6]:
            tek_jobs.append(job[1])
    
    print(f"\nJobs requiring Cel Holzher: {', '.join(cel_jobs) if cel_jobs else 'None'}")
    print(f"Jobs requiring Tekenbureel: {', '.join(tek_jobs) if tek_jobs else 'None'}")
    
    print(f"\nPeople skilled in Cel Holzher ({len(cel_holzher_operators)}):")
    for op in cel_holzher_operators:
        print(f"   - {op[0]} (Level {op[1]})")
    
    print(f"\nPeople skilled in Tekenbureel ({len(tekenbureel_operators)}):")
    for op in tekenbureel_operators:
        print(f"   - {op[0]} (Level {op[1]})")
    
    # Check machine max operators
    c.execute("SELECT name, max_operators FROM machines WHERE name IN ('Cel Holzher', 'Tekenbureel')")
    max_ops = dict(c.fetchall())
    
    print(f"\nMachine Capacity:")
    print(f"   - Cel Holzher: Max {max_ops.get('Cel Holzher', 'N/A')} operators")
    print(f"   - Tekenbureel: Max {max_ops.get('Tekenbureel', 'N/A')} operators")
    
    print("\n" + "=" * 80)
    print("ALGORITHM LOGIC EXPLANATION:")
    print("=" * 80)
    print("""
The scheduling algorithm assigned operators based on:

1. JOB PRIORITY AND SEQUENCE:
   - Jobs are processed in order of priority (high first) and due date
   - Each job specifies which machines it needs in sequence
   
2. MACHINE CAPACITY:
   - Cel Holzher allows up to {} operators simultaneously
   - Tekenbureel allows up to {} operators simultaneously
   
3. SKILL MATCHING:
   - Algorithm finds people with skills for required machines
   - Higher skill levels are preferred for high-priority jobs
   
4. ASSIGNMENT PROCESS:
   - For each job, the algorithm:
     a) Identifies required machines from the job's machine_sequence
     b) Checks available operators with skills for that machine
     c) Assigns up to max_operators people to work in parallel
     d) Moves to next machine in sequence or next job

The result (3 on Cel Holzher, 1 on Tekenbureel) suggests:
- The 'maatwerk' job required Cel Holzher and had enough work for 3 operators
- The 'Tekenwerk' job required Tekenbureel and needed only 1 operator
- The algorithm maximized throughput by using parallel operators where beneficial
""".format(max_ops.get('Cel Holzher', 'N/A'), max_ops.get('Tekenbureel', 'N/A')))
    
    conn.close()

if __name__ == '__main__':
    analyze_schedule()