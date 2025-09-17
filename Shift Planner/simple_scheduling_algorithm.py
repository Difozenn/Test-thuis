#!/usr/bin/env python3
"""Simplified scheduling algorithm - full day assignments, no time calculations"""

import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
from scheduling_algorithm import SchedulingAlgorithm

class SimpleSchedulingAlgorithm(SchedulingAlgorithm):
    """Simple algorithm that assigns people to machines for full days"""
    
    def get_disabled_machines(self, schedule_date):
        """Get list of machine IDs that are disabled for a specific date"""
        conn = sqlite3.connect(self.database)
        c = conn.cursor()
        
        c.execute('SELECT machine_id FROM disabled_machines WHERE date = ?', 
                 (schedule_date.isoformat(),))
        
        disabled = set(row[0] for row in c.fetchall())
        conn.close()
        return disabled
    
    def is_machine_complete_for_job(self, job_id, machine_id):
        """Check if a specific machine has completed its portion of a job"""
        conn = sqlite3.connect(self.database)
        c = conn.cursor()
        
        # Get job quantity
        c.execute('SELECT quantity FROM jobs WHERE id = ?', (job_id,))
        result = c.fetchone()
        if not result:
            conn.close()
            return False
        
        total_quantity = result[0] if result[0] is not None else 0
        
        # Check if machine has completed this quantity
        c.execute('''SELECT completed_quantity FROM job_progress 
                    WHERE job_id = ? AND machine_id = ?''',
                 (job_id, machine_id))
        progress = c.fetchone()
        
        conn.close()
        
        if progress and progress[0] >= total_quantity:
            return True
        return False
    
    def detect_bottlenecks(self, jobs, machines):
        """Detect machines that are bottlenecks in the workflow"""
        bottlenecks = {}
        
        for job in jobs:
            if not job.get('sequential', False):
                continue  # Only check sequential jobs for bottlenecks
            
            # Parse machine sequence
            if isinstance(job['machine_sequence'], list):
                sequence = job['machine_sequence']
            else:
                sequence = [m.strip() for m in job['machine_sequence'].split(',')]
            
            # Find which machines are blocking others
            blocked_machines = []
            for i, machine_name in enumerate(sequence):
                # Find machine ID
                machine_id = None
                for m_id, m_info in machines.items():
                    if m_info['name'] == machine_name:
                        machine_id = m_id
                        break
                
                if not machine_id:
                    continue
                
                # Check if this machine has completed its work
                if not self.is_machine_complete_for_job(job['id'], machine_id):
                    # This machine is not complete, all following machines are blocked
                    for j in range(i + 1, len(sequence)):
                        blocked_machines.append((sequence[j], machine_name, job['id']))
                    break  # No need to check further machines in sequence
            
            # Record bottlenecks
            for blocked, blocking, job_id in blocked_machines:
                if blocking not in bottlenecks:
                    bottlenecks[blocking] = {
                        'blocking_count': 0,
                        'blocked_machines': set(),
                        'jobs_affected': set()
                    }
                bottlenecks[blocking]['blocking_count'] += 1
                bottlenecks[blocking]['blocked_machines'].add(blocked)
                bottlenecks[blocking]['jobs_affected'].add(job_id)
        
        return bottlenecks
    
    def calculate_machine_urgency(self, machine_id, machine_name, jobs, machines):
        """Calculate urgency score for a machine based on workflow dependencies"""
        urgency_score = 0
        
        for job in jobs:
            if not job.get('sequential', False):
                continue
            
            # Parse machine sequence
            if isinstance(job['machine_sequence'], list):
                sequence = job['machine_sequence']
            else:
                sequence = [m.strip() for m in job['machine_sequence'].split(',')]
            
            if machine_name not in sequence:
                continue
            
            # Higher urgency if this machine is early in sequence
            position = sequence.index(machine_name)
            machines_waiting = len(sequence) - position - 1
            
            # Factor in job priority
            job_priority = job.get('priority', 0)
            
            # Calculate urgency: more waiting machines + higher priority = higher urgency
            urgency_score += (machines_waiting * 2) + (job_priority * 5)
            
            # Extra urgency if this is the current bottleneck
            if not self.is_machine_complete_for_job(job['id'], machine_id):
                urgency_score += 10
        
        return urgency_score
    
    def can_machine_start_sequential_job(self, job, machine_id, machines):
        """Check if a machine can start working on a sequential job"""
        if not job.get('sequential', False):
            return True  # Non-sequential jobs can always start
        
        # Parse machine sequence to get ordered list
        if isinstance(job['machine_sequence'], list):
            sequence = job['machine_sequence']
        else:
            sequence = [m.strip() for m in job['machine_sequence'].split(',')]
        
        # Convert machine names to IDs in order
        ordered_machine_ids = []
        for machine_name in sequence:
            for m_id, m_info in machines.items():
                if m_info['name'] == machine_name:
                    ordered_machine_ids.append(m_id)
                    break
        
        # Find position of current machine
        try:
            machine_position = ordered_machine_ids.index(machine_id)
        except ValueError:
            return True  # Machine not in sequence, can start
        
        if machine_position == 0:
            return True  # First machine, can start
        
        # Check if all previous machines have completed
        for i in range(machine_position):
            prev_machine_id = ordered_machine_ids[i]
            if not self.is_machine_complete_for_job(job['id'], prev_machine_id):
                return False  # Previous machine not complete
        
        return True
    
    def schedule_day(self, schedule_date, machines):
        """Schedule operators for full day shifts"""
        assignments = []
        available_people = self.get_available_people(schedule_date)
        jobs = self.get_pending_jobs(schedule_date + timedelta(days=30))  # Look ahead 30 days
        
        if not available_people or not machines or not jobs:
            print(f"Skipping {schedule_date}: People={len(available_people)}, Machines={len(machines)}, Jobs={len(jobs)}")
            return assignments
        
        # Get disabled machines for this date
        disabled_machines = self.get_disabled_machines(schedule_date)
        
        # Build job-machine mapping
        job_machine_map = defaultdict(set)  # job_id -> set of machine_ids needed
        all_machines_needed = set()
        job_priorities = {}
        
        for job in jobs:
            if not job['machine_sequence']:
                continue
            
            job_priorities[job['id']] = job.get('priority', 0)
            
            # Parse machine sequence
            if isinstance(job['machine_sequence'], list):
                sequence = job['machine_sequence']
            else:
                sequence = [m.strip() for m in job['machine_sequence'].split(',')]
            
            # Find machine IDs for all machines in sequence
            for machine_name in sequence:
                for m_id, m_info in machines.items():
                    if m_info['name'] == machine_name:
                        job_machine_map[job['id']].add(m_id)
                        all_machines_needed.add(m_id)
                        break
        
        if not all_machines_needed:
            print("No machines needed for jobs")
            return assignments
        
        # Get people skills
        people_skills = {}
        for person in available_people:
            skills = self.get_person_skills(person['id'])
            people_skills[person['id']] = {
                'name': person['name'],
                'skills': skills
            }
        
        # Track assignments
        machine_assignments = defaultdict(list)  # machine_id -> list of person_ids
        assigned_people = set()
        
        # Check for high priority work
        has_high_priority = any(p > 0 for p in job_priorities.values())
        
        # Detect bottlenecks in the workflow
        bottlenecks = self.detect_bottlenecks(jobs, machines)
        
        # Calculate urgency scores for each machine
        machine_urgency = {}
        for machine_id, machine_info in machines.items():
            if machine_id in all_machines_needed:
                urgency = self.calculate_machine_urgency(machine_id, machine_info['name'], jobs, machines)
                machine_urgency[machine_id] = urgency
        
        print(f"\nScheduling for {schedule_date}:")
        print("-" * 50)
        
        # Report bottlenecks
        if bottlenecks:
            print("\nBottleneck Analysis:")
            for machine_name, info in bottlenecks.items():
                print(f"  {machine_name} is blocking {info['blocking_count']} downstream machines")
                print(f"    Blocked: {', '.join(info['blocked_machines'])}")
        
        # Sort machines by urgency for processing order
        machines_by_urgency = sorted(all_machines_needed, 
                                     key=lambda m: machine_urgency.get(m, 0), 
                                     reverse=True)
        
        # Phase 1: Ensure minimum operators for each machine (process by urgency)
        for machine_id in machines_by_urgency:
            # Skip disabled machines
            if machine_id in disabled_machines:
                print(f"Skipping disabled machine {machine_id} for {schedule_date}")
                continue
                
            machine_info = machines[machine_id]
            min_operators = machine_info.get('min_operators', 1)
            machine_name = machine_info['name']
            
            # Find which job needs this machine (prioritize high priority jobs)
            job_for_machine = None
            candidate_jobs = []
            
            for job_id, machine_ids in job_machine_map.items():
                if machine_id in machine_ids:
                    # Check if this machine has already completed this job
                    if self.is_machine_complete_for_job(job_id, machine_id):
                        print(f"  Machine {machine_name} already completed job {job_id}")
                        continue
                    
                    # Find the actual job object
                    for job in jobs:
                        if job['id'] == job_id:
                            # Check if machine can start (for sequential jobs)
                            if not self.can_machine_start_sequential_job(job, machine_id, machines):
                                print(f"  Machine {machine_name} waiting for previous machines to complete job {job_id}")
                                continue
                            candidate_jobs.append(job)
                            break
            
            # Sort candidate jobs by priority (highest first), then by due date
            if candidate_jobs:
                candidate_jobs.sort(key=lambda j: (-j.get('priority', 0), j.get('due_date', '9999-12-31')))
                job_for_machine = candidate_jobs[0]
            
            if not job_for_machine:
                continue
            
            # Check if this is high priority
            is_high_priority = job_for_machine.get('priority', 0) > 0
            
            # Determine if we should override minimum operators
            is_bottleneck = machine_name in bottlenecks
            
            # Smart minimum override logic:
            # 1. Keep minimum if this machine is a bottleneck (needs resources)
            # 2. Keep minimum if this is high priority work
            # 3. Otherwise, can reduce minimum if needed for bottlenecks elsewhere
            should_keep_minimum = is_bottleneck or is_high_priority
            
            # Only override minimum if:
            # - There are bottlenecks elsewhere that need resources
            # - This machine is not itself a bottleneck
            # - This is not high priority work
            if bottlenecks and not should_keep_minimum:
                # Check if any bottleneck needs more resources
                for bn_name, bn_info in bottlenecks.items():
                    if bn_info['blocking_count'] > 2:  # Significant bottleneck
                        min_operators = 0  # Allow reallocation
                        print(f"  Allowing reallocation from {machine_name} due to bottleneck at {bn_name}")
                        break
            
            print(f"\n{machine_name}: needs min {min_operators} operators")
            
            # Find available people with skills for this machine
            available_for_machine = []
            for person_id, person_info in people_skills.items():
                if person_id in assigned_people:
                    continue
                    
                if machine_id not in person_info['skills']:
                    continue
                
                skill_level = person_info['skills'][machine_id]['level']
                
                # Check precision requirement
                if job_for_machine.get('precision_required', False) and skill_level < 4:
                    continue
                
                available_for_machine.append({
                    'person_id': person_id,
                    'name': person_info['name'],
                    'skill_level': skill_level
                })
            
            # Sort by skill level (highest first)
            available_for_machine.sort(key=lambda x: x['skill_level'], reverse=True)
            
            # Assign minimum operators
            operators_assigned = 0
            for person in available_for_machine[:min_operators]:
                assignment = {
                    'date': schedule_date.isoformat(),
                    'machine_id': machine_id,
                    'person_id': person['person_id'],
                    'job_id': job_for_machine['id'],
                    'start_time': '07:30',  # Fixed start time
                    'end_time': '16:00'     # Fixed end time
                }
                
                assignments.append(assignment)
                machine_assignments[machine_id].append(person['person_id'])
                assigned_people.add(person['person_id'])
                operators_assigned += 1
                print(f"  Assigned: {person['name']} (Level {person['skill_level']})")
            
            if operators_assigned < min_operators:
                print(f"  WARNING: Only {operators_assigned}/{min_operators} operators assigned")
        
        # Phase 2: Assign additional operators up to maximum (prioritize bottlenecks)
        print("\nPhase 2: Assigning additional operators (prioritizing bottlenecks)...")
        
        # Process machines by urgency to ensure bottlenecks get resources first
        for machine_id in machines_by_urgency:
            # Skip disabled machines
            if machine_id in disabled_machines:
                continue
                
            machine_info = machines[machine_id]
            max_operators = machine_info['max_operators']
            current_count = len(machine_assignments[machine_id])
            
            if current_count >= max_operators:
                continue
            
            machine_name = machine_info['name']
            additional_slots = max_operators - current_count
            
            # Find job for this machine (prioritize high priority jobs)
            job_for_machine = None
            candidate_jobs = []
            
            for job_id, machine_ids in job_machine_map.items():
                if machine_id in machine_ids:
                    # Check if this machine has already completed this job
                    if self.is_machine_complete_for_job(job_id, machine_id):
                        continue
                    
                    for job in jobs:
                        if job['id'] == job_id:
                            # Check if machine can start (for sequential jobs)
                            if not self.can_machine_start_sequential_job(job, machine_id, machines):
                                continue
                            candidate_jobs.append(job)
                            break
            
            # Sort candidate jobs by priority (highest first), then by due date
            if candidate_jobs:
                candidate_jobs.sort(key=lambda j: (-j.get('priority', 0), j.get('due_date', '9999-12-31')))
                job_for_machine = candidate_jobs[0]
            
            if not job_for_machine:
                continue
            
            # Find additional available people
            available_for_machine = []
            for person_id, person_info in people_skills.items():
                if person_id in assigned_people:
                    continue
                    
                if machine_id not in person_info['skills']:
                    continue
                
                skill_level = person_info['skills'][machine_id]['level']
                
                # Check precision requirement
                if job_for_machine.get('precision_required', False) and skill_level < 4:
                    continue
                
                available_for_machine.append({
                    'person_id': person_id,
                    'name': person_info['name'],
                    'skill_level': skill_level
                })
            
            # Sort by skill level
            available_for_machine.sort(key=lambda x: x['skill_level'], reverse=True)
            
            # Assign additional operators
            for person in available_for_machine[:additional_slots]:
                assignment = {
                    'date': schedule_date.isoformat(),
                    'machine_id': machine_id,
                    'person_id': person['person_id'],
                    'job_id': job_for_machine['id'],
                    'start_time': '07:30',
                    'end_time': '16:00'
                }
                
                assignments.append(assignment)
                machine_assignments[machine_id].append(person['person_id'])
                assigned_people.add(person['person_id'])
                print(f"  {machine_name}: Added {person['name']} (Level {person['skill_level']})")
        
        # Summary
        print(f"\n" + "=" * 50)
        print(f"Day {schedule_date} Summary:")
        print(f"  Total assignments: {len(assignments)}")
        print(f"  Machines with operators: {len(machine_assignments)}")
        print(f"  People working: {len(assigned_people)}/{len(available_people)}")
        
        # Show machine coverage
        for machine_id, person_ids in machine_assignments.items():
            machine_name = machines[machine_id]['name']
            min_req = machines[machine_id].get('min_operators', 1)
            max_req = machines[machine_id]['max_operators']
            status = "✓" if len(person_ids) >= min_req else "✗"
            print(f"  {status} {machine_name}: {len(person_ids)} operators (min:{min_req}, max:{max_req})")
        
        return assignments