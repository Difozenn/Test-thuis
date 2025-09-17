#!/usr/bin/env python3
"""Sequential scheduling algorithm that handles machine sequences properly"""

import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
from scheduling_algorithm import SchedulingAlgorithm

class SequentialSchedulingAlgorithm(SchedulingAlgorithm):
    """Algorithm that schedules operators for all machines in job sequences"""
    
    def schedule_day(self, schedule_date, machines):
        """Schedule operators for all machines in job sequences"""
        assignments = []
        available_people = self.get_available_people(schedule_date)
        jobs = self.get_pending_jobs(schedule_date + timedelta(days=7))
        
        if not available_people or not machines or not jobs:
            print(f"Skipping {schedule_date}: People={len(available_people)}, Machines={len(machines)}, Jobs={len(jobs)}")
            return assignments
        
        # Build job-machine mapping
        job_machine_map = defaultdict(list)  # job_id -> [(machine_id, machine_name, sequence_order)]
        all_machines_needed = set()
        
        for job in jobs:
            if not job['machine_sequence']:
                continue
            
            # Handle both string and list formats
            if isinstance(job['machine_sequence'], list):
                sequence = job['machine_sequence']
            else:
                sequence = [m.strip() for m in job['machine_sequence'].split(',')]
            
            for seq_order, machine_name in enumerate(sequence):
                for m_id, m_info in machines.items():
                    if m_info['name'] == machine_name:
                        job_machine_map[job['id']].append((m_id, machine_name, seq_order))
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
        machine_assignments = defaultdict(list)
        person_assignments = {}  # person_id -> list of (machine_id, start_time, end_time)
        
        # Calculate time slots for each machine in sequence
        # Assumption: Each stage takes proportion of total time
        total_hours = self.shift_duration.total_seconds() / 3600
        
        # Process each job and its machine sequence
        for job in jobs:
            if job['id'] not in job_machine_map:
                continue
            
            job_machines = job_machine_map[job['id']]
            num_stages = len(job_machines)
            
            if num_stages == 0:
                continue
            
            # Calculate time per stage (equal division for simplicity)
            hours_per_stage = total_hours / num_stages
            
            print(f"\nScheduling job: {job['name']} with {num_stages} stages")
            
            # Schedule each machine in the sequence
            for machine_id, machine_name, seq_order in job_machines:
                machine_info = machines[machine_id]
                min_operators = machine_info.get('min_operators', 1)
                max_operators = machine_info['max_operators']
                
                # Calculate time slot for this stage
                start_offset = seq_order * hours_per_stage
                start_time_td = self.shift_start + timedelta(hours=start_offset)
                end_time_td = start_time_td + timedelta(hours=hours_per_stage)
                
                # Ensure within shift bounds
                if end_time_td > self.shift_end:
                    end_time_td = self.shift_end
                if start_time_td >= self.shift_end:
                    continue  # Skip if stage would start after shift ends
                
                print(f"  Stage {seq_order + 1}: {machine_name} ({self.timedelta_to_time(start_time_td)}-{self.timedelta_to_time(end_time_td)})")
                
                # Find available people for this machine and time slot
                available_for_machine = []
                
                for person_id, person_info in people_skills.items():
                    # Check if person has skill for this machine
                    if machine_id not in person_info['skills']:
                        continue
                    
                    # Check if person is available during this time slot
                    if person_id in person_assignments:
                        # Check for time conflicts
                        is_available = True
                        for assigned_machine, assigned_start, assigned_end in person_assignments[person_id]:
                            # Check for overlap
                            if not (end_time_td <= assigned_start or start_time_td >= assigned_end):
                                is_available = False
                                break
                        
                        if not is_available:
                            continue
                    
                    skill_level = person_info['skills'][machine_id]['level']
                    
                    # Check precision requirement
                    if job.get('precision_required', False) and skill_level < 4:
                        continue
                    
                    available_for_machine.append({
                        'person_id': person_id,
                        'name': person_info['name'],
                        'skill_level': skill_level
                    })
                
                # Sort by skill level (highest first)
                available_for_machine.sort(key=lambda x: x['skill_level'], reverse=True)
                
                # Assign operators (respect min/max but try to use more people)
                # For first stage (Cel Holzher), we can use more operators since they work in parallel
                # For sequential stages, we want to ensure good coverage
                if seq_order == 0:  # First stage - can use more operators
                    operators_to_assign = min(max_operators, len(available_for_machine))
                else:  # Later stages - use what's optimal
                    operators_to_assign = min(
                        max(min_operators, 2),  # Try to use at least 2 if available
                        min(max_operators, len(available_for_machine))
                    )
                
                assigned_count = 0
                for person in available_for_machine[:operators_to_assign]:
                    assignment = {
                        'date': schedule_date.isoformat(),
                        'machine_id': machine_id,
                        'person_id': person['person_id'],
                        'job_id': job['id'],
                        'start_time': self.timedelta_to_time(start_time_td),
                        'end_time': self.timedelta_to_time(end_time_td)
                    }
                    
                    assignments.append(assignment)
                    machine_assignments[machine_id].append(assignment)
                    
                    # Track person's schedule
                    if person['person_id'] not in person_assignments:
                        person_assignments[person['person_id']] = []
                    person_assignments[person['person_id']].append(
                        (machine_id, start_time_td, end_time_td)
                    )
                    
                    assigned_count += 1
                    print(f"    Assigned: {person['name']} (Level {person['skill_level']})")
                
                if assigned_count == 0:
                    print(f"    WARNING: No operators available for {machine_name}!")
                elif assigned_count < min_operators:
                    print(f"    WARNING: Only {assigned_count}/{min_operators} minimum operators assigned")
        
        # Summary
        print(f"\n{'-' * 50}")
        print(f"Total assignments: {len(assignments)}")
        print(f"Machines scheduled: {len(machine_assignments)}")
        print(f"People assigned: {len(person_assignments)}")
        
        return assignments