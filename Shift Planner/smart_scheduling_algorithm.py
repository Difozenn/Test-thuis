#!/usr/bin/env python3
"""Smarter scheduling algorithm that respects minimum operators and handles multi-skilled workers better"""

import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
from scheduling_algorithm import SchedulingAlgorithm

class SmartSchedulingAlgorithm(SchedulingAlgorithm):
    """Enhanced scheduling algorithm with better minimum operator handling"""
    
    def analyze_worker_skills(self, available_people, machines_needed):
        """Analyze which workers are critical for certain machines"""
        worker_analysis = {}
        
        for person in available_people:
            skills = self.get_person_skills(person['id'])
            machines_can_operate = set()
            
            for machine_id in machines_needed:
                if machine_id in skills:
                    machines_can_operate.add(machine_id)
            
            worker_analysis[person['id']] = {
                'name': person['name'],
                'machines': machines_can_operate,
                'is_multi_skilled': len(machines_can_operate) > 1,
                'skills': skills
            }
        
        return worker_analysis
    
    def find_critical_assignments(self, worker_analysis, machine_requirements):
        """Identify critical worker assignments to meet minimum requirements"""
        critical_assignments = []
        machine_available_workers = defaultdict(list)
        
        # Find which workers can operate each machine
        for worker_id, info in worker_analysis.items():
            for machine_id in info['machines']:
                machine_available_workers[machine_id].append(worker_id)
        
        # Identify machines with limited worker options
        for machine_id, min_required in machine_requirements.items():
            available = machine_available_workers[machine_id]
            if len(available) <= min_required:
                # All these workers are critical for this machine
                for worker_id in available:
                    critical_assignments.append((worker_id, machine_id))
        
        return critical_assignments, machine_available_workers
    
    def schedule_day(self, schedule_date, machines):
        """Enhanced scheduling that respects minimum operators better"""
        assignments = []
        available_people = self.get_available_people(schedule_date)
        jobs = self.get_pending_jobs(schedule_date + timedelta(days=7))
        
        if not available_people or not machines or not jobs:
            print(f"Skipping {schedule_date}: People={len(available_people)}, Machines={len(machines)}, Jobs={len(jobs)}")
            return assignments
        
        # Analyze job requirements
        job_machine_map = defaultdict(list)
        machines_needed_today = set()
        job_priorities = {}
        
        for job in jobs:
            if not job['machine_sequence']:
                continue
            
            job_priorities[job['id']] = job.get('priority', 0)
            
            for machine_name in job['machine_sequence']:
                for m_id, m_info in machines.items():
                    if m_info['name'] == machine_name:
                        job_machine_map[job['id']].append(m_id)
                        machines_needed_today.add(m_id)
                        break
        
        if not machines_needed_today:
            return assignments
        
        # Get minimum requirements for each machine
        machine_min_requirements = {}
        for m_id in machines_needed_today:
            machine_min_requirements[m_id] = machines[m_id].get('min_operators', 1)
        
        # Analyze worker skills and critical assignments
        worker_analysis = self.analyze_worker_skills(available_people, machines_needed_today)
        critical_assignments, machine_available_workers = self.find_critical_assignments(
            worker_analysis, machine_min_requirements
        )
        
        # Track assignments
        machine_assignments = defaultdict(list)
        assigned_people = set()
        
        # Check for high priority jobs
        has_high_priority = any(p > 0 for p in job_priorities.values())
        
        # Phase 1: Ensure minimum operators per machine
        # Prioritize single-skilled workers first, save multi-skilled for where they're needed
        for machine_id in machines_needed_today:
            min_needed = machine_min_requirements[machine_id]
            
            # Skip minimum if there's high priority work and this isn't it
            if has_high_priority:
                machine_has_high_priority = False
                for job_id, machines_list in job_machine_map.items():
                    if machine_id in machines_list and job_priorities[job_id] > 0:
                        machine_has_high_priority = True
                        break
                
                if not machine_has_high_priority:
                    min_needed = 0  # Allow skipping minimum for non-priority machines
            
            # Find workers for this machine
            available_workers = machine_available_workers[machine_id]
            
            # Sort workers: prefer single-skilled for this machine first
            workers_sorted = []
            for worker_id in available_workers:
                if worker_id in assigned_people:
                    continue
                
                worker_info = worker_analysis[worker_id]
                # Prioritize workers who can ONLY work this machine
                if len(worker_info['machines']) == 1:
                    workers_sorted.insert(0, worker_id)  # Add to front
                else:
                    workers_sorted.append(worker_id)  # Add to back
            
            # Assign minimum operators
            operators_assigned = 0
            for worker_id in workers_sorted[:min_needed]:
                if worker_id in assigned_people:
                    continue
                
                # Find the job for this machine
                job_for_machine = None
                for job in jobs:
                    if job['id'] in job_machine_map and machine_id in job_machine_map[job['id']]:
                        job_for_machine = job
                        break
                
                if not job_for_machine:
                    continue
                
                # Create assignment
                worker_info = worker_analysis[worker_id]
                skill_level = worker_info['skills'][machine_id]['level']
                
                job_hours = self.calculate_job_time(
                    job_for_machine, skill_level, machines[machine_id]['base_throughput']
                )
                
                start_time_td = self.shift_start
                end_time_td = start_time_td + timedelta(hours=job_hours)
                
                if end_time_td > self.shift_end:
                    end_time_td = self.shift_end
                
                assignment = {
                    'date': schedule_date.isoformat(),
                    'machine_id': machine_id,
                    'person_id': worker_id,
                    'job_id': job_for_machine['id'],
                    'start_time': self.timedelta_to_time(start_time_td),
                    'end_time': self.timedelta_to_time(end_time_td)
                }
                
                assignments.append(assignment)
                assigned_people.add(worker_id)
                machine_assignments[machine_id].append(assignment)
                operators_assigned += 1
                
                print(f"Assigned {worker_info['name']} to {machines[machine_id]['name']} (min requirement)")
        
        # Phase 2: Assign remaining workers to maximize throughput
        for machine_id in machines_needed_today:
            max_operators = machines[machine_id]['max_operators']
            current_count = len(machine_assignments[machine_id])
            
            if current_count >= max_operators:
                continue
            
            # Find additional workers
            available_workers = machine_available_workers[machine_id]
            
            for worker_id in available_workers:
                if worker_id in assigned_people:
                    continue
                
                if len(machine_assignments[machine_id]) >= max_operators:
                    break
                
                # Find the job for this machine
                job_for_machine = None
                for job in jobs:
                    if job['id'] in job_machine_map and machine_id in job_machine_map[job['id']]:
                        job_for_machine = job
                        break
                
                if not job_for_machine:
                    continue
                
                # Create assignment
                worker_info = worker_analysis[worker_id]
                skill_level = worker_info['skills'][machine_id]['level']
                
                job_hours = self.calculate_job_time(
                    job_for_machine, skill_level, machines[machine_id]['base_throughput']
                )
                
                # Adjust for parallel work
                job_hours = job_hours / (len(machine_assignments[machine_id]) + 1)
                
                start_time_td = self.shift_start
                end_time_td = start_time_td + timedelta(hours=job_hours)
                
                if end_time_td > self.shift_end:
                    end_time_td = self.shift_end
                
                assignment = {
                    'date': schedule_date.isoformat(),
                    'machine_id': machine_id,
                    'person_id': worker_id,
                    'job_id': job_for_machine['id'],
                    'start_time': self.timedelta_to_time(start_time_td),
                    'end_time': self.timedelta_to_time(end_time_td)
                }
                
                assignments.append(assignment)
                assigned_people.add(worker_id)
                machine_assignments[machine_id].append(assignment)
                
                print(f"Assigned {worker_info['name']} to {machines[machine_id]['name']} (additional capacity)")
        
        return assignments