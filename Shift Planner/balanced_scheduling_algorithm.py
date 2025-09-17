#!/usr/bin/env python3
"""Balanced scheduling algorithm that respects minimum operators for all machines"""

import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
from scheduling_algorithm import SchedulingAlgorithm

class BalancedSchedulingAlgorithm(SchedulingAlgorithm):
    """Algorithm that ensures all machines get minimum operators before maximizing"""
    
    def schedule_day(self, schedule_date, machines):
        """Schedule operators ensuring all minimums are met first"""
        assignments = []
        available_people = self.get_available_people(schedule_date)
        jobs = self.get_pending_jobs(schedule_date + timedelta(days=7))
        
        if not available_people or not machines or not jobs:
            print(f"Skipping {schedule_date}: People={len(available_people)}, Machines={len(machines)}, Jobs={len(jobs)}")
            return assignments
        
        # Build complete job-machine-time mapping
        job_machine_map = defaultdict(list)  # job_id -> [(machine_id, machine_name, start_time, end_time)]
        all_machines_needed = set()
        job_priorities = {}
        
        # Calculate time slots for sequential operations
        total_hours = self.shift_duration.total_seconds() / 3600
        
        for job in jobs:
            if not job['machine_sequence']:
                continue
            
            job_priorities[job['id']] = job.get('priority', 0)
            
            # Handle both string and list formats
            if isinstance(job['machine_sequence'], list):
                sequence = job['machine_sequence']
            else:
                sequence = [m.strip() for m in job['machine_sequence'].split(',')]
            
            num_stages = len(sequence)
            hours_per_stage = total_hours / num_stages if num_stages > 0 else total_hours
            
            for seq_order, machine_name in enumerate(sequence):
                for m_id, m_info in machines.items():
                    if m_info['name'] == machine_name:
                        # Calculate time slot for this stage
                        start_offset = seq_order * hours_per_stage
                        start_time = self.shift_start + timedelta(hours=start_offset)
                        end_time = start_time + timedelta(hours=hours_per_stage)
                        
                        # Ensure within shift bounds
                        if end_time > self.shift_end:
                            end_time = self.shift_end
                        if start_time >= self.shift_end:
                            continue
                        
                        job_machine_map[job['id']].append((m_id, machine_name, start_time, end_time))
                        all_machines_needed.add(m_id)
                        break
        
        if not all_machines_needed:
            print("No machines needed for jobs")
            return assignments
        
        # Get people skills for all machines
        people_skills = {}
        for person in available_people:
            skills = self.get_person_skills(person['id'])
            people_skills[person['id']] = {
                'name': person['name'],
                'skills': skills
            }
        
        # Track assignments
        machine_assignments = defaultdict(list)  # machine_id -> list of assignments
        person_schedule = {}  # person_id -> list of (start_time, end_time, machine_id)
        
        # Check if we have high priority jobs
        has_high_priority = any(p > 0 for p in job_priorities.values())
        
        print("\n" + "=" * 80)
        print("PHASE 1: ENSURE ALL MACHINES GET MINIMUM OPERATORS")
        print("=" * 80)
        
        # First pass: Ensure all machines get their minimum operators
        for machine_id in all_machines_needed:
            machine_info = machines[machine_id]
            min_operators = machine_info.get('min_operators', 1)
            machine_name = machine_info['name']
            
            print(f"\n{machine_name}: Requires minimum {min_operators} operators")
            
            # Find all time slots this machine needs coverage
            machine_time_slots = []
            for job_id, machines_list in job_machine_map.items():
                for m_id, m_name, start_time, end_time in machines_list:
                    if m_id == machine_id:
                        machine_time_slots.append((start_time, end_time, job_id))
            
            if not machine_time_slots:
                continue
            
            # For simplicity, take the earliest/longest time slot
            machine_time_slots.sort(key=lambda x: (x[0], -((x[1] - x[0]).total_seconds())))
            start_time, end_time, job_id = machine_time_slots[0]
            
            # Check if this machine has high priority work
            machine_has_high_priority = job_priorities.get(job_id, 0) > 0
            
            # Override minimum only if there's high priority work elsewhere and this isn't it
            if has_high_priority and not machine_has_high_priority:
                print(f"  (Can be overridden - no high priority work)")
                min_operators = 0
            
            # Find available people for this machine
            available_for_machine = []
            for person_id, person_info in people_skills.items():
                if machine_id not in person_info['skills']:
                    continue
                
                # Check if person is available during this time
                if person_id in person_schedule:
                    is_available = True
                    for scheduled_start, scheduled_end, scheduled_machine in person_schedule[person_id]:
                        if not (end_time <= scheduled_start or start_time >= scheduled_end):
                            is_available = False
                            break
                    if not is_available:
                        continue
                
                skill_level = person_info['skills'][machine_id]['level']
                available_for_machine.append({
                    'person_id': person_id,
                    'name': person_info['name'],
                    'skill_level': skill_level
                })
            
            # Sort by skill level (highest first)
            available_for_machine.sort(key=lambda x: x['skill_level'], reverse=True)
            
            # Assign minimum operators
            assigned_count = 0
            for person in available_for_machine[:min_operators]:
                assignment = {
                    'date': schedule_date.isoformat(),
                    'machine_id': machine_id,
                    'person_id': person['person_id'],
                    'job_id': job_id,
                    'start_time': self.timedelta_to_time(start_time),
                    'end_time': self.timedelta_to_time(end_time)
                }
                
                assignments.append(assignment)
                machine_assignments[machine_id].append(assignment)
                
                # Track person's schedule
                if person['person_id'] not in person_schedule:
                    person_schedule[person['person_id']] = []
                person_schedule[person['person_id']].append((start_time, end_time, machine_id))
                
                assigned_count += 1
                print(f"  Assigned: {person['name']} (Level {person['skill_level']})")
            
            if assigned_count < min_operators:
                print(f"  WARNING: Only {assigned_count}/{min_operators} minimum operators assigned!")
        
        print("\n" + "=" * 80)
        print("PHASE 2: ASSIGN ADDITIONAL OPERATORS WHERE BENEFICIAL")
        print("=" * 80)
        
        # Second pass: Assign additional operators up to maximum
        for job_id, machines_list in job_machine_map.items():
            for machine_id, machine_name, start_time, end_time in machines_list:
                machine_info = machines[machine_id]
                max_operators = machine_info['max_operators']
                current_count = len([a for a in machine_assignments[machine_id] 
                                    if a['job_id'] == job_id])
                
                if current_count >= max_operators:
                    continue
                
                print(f"\n{machine_name}: Can take {max_operators - current_count} more operators")
                
                # Find additional available people
                available_for_machine = []
                for person_id, person_info in people_skills.items():
                    if machine_id not in person_info['skills']:
                        continue
                    
                    # Check if person is available during this time
                    if person_id in person_schedule:
                        is_available = True
                        for scheduled_start, scheduled_end, scheduled_machine in person_schedule[person_id]:
                            if not (end_time <= scheduled_start or start_time >= scheduled_end):
                                is_available = False
                                break
                        if not is_available:
                            continue
                    
                    skill_level = person_info['skills'][machine_id]['level']
                    available_for_machine.append({
                        'person_id': person_id,
                        'name': person_info['name'],
                        'skill_level': skill_level
                    })
                
                # Sort by skill level
                available_for_machine.sort(key=lambda x: x['skill_level'], reverse=True)
                
                # Assign additional operators
                additional_to_assign = min(max_operators - current_count, len(available_for_machine))
                for person in available_for_machine[:additional_to_assign]:
                    assignment = {
                        'date': schedule_date.isoformat(),
                        'machine_id': machine_id,
                        'person_id': person['person_id'],
                        'job_id': job_id,
                        'start_time': self.timedelta_to_time(start_time),
                        'end_time': self.timedelta_to_time(end_time)
                    }
                    
                    assignments.append(assignment)
                    machine_assignments[machine_id].append(assignment)
                    
                    if person['person_id'] not in person_schedule:
                        person_schedule[person['person_id']] = []
                    person_schedule[person['person_id']].append((start_time, end_time, machine_id))
                    
                    print(f"  Additional: {person['name']} (Level {person['skill_level']})")
        
        # Summary
        print(f"\n" + "=" * 80)
        print(f"Total assignments: {len(assignments)}")
        print(f"Machines scheduled: {len(machine_assignments)}")
        print(f"People assigned: {len(person_schedule)}")
        
        return assignments