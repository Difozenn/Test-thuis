import sqlite3
from datetime import datetime, timedelta, date
from collections import defaultdict
import heapq

class SchedulingAlgorithm:
    def __init__(self, database):
        self.database = database
        self.shift_start = timedelta(hours=7, minutes=30)
        self.shift_end = timedelta(hours=16)
        self.shift_duration = self.shift_end - self.shift_start
        
    def get_available_people(self, target_date):
        conn = sqlite3.connect(self.database)
        c = conn.cursor()
        
        c.execute('''SELECT p.id, p.name FROM people p
                    WHERE p.id NOT IN (
                        SELECT person_id FROM availability 
                        WHERE date = ? AND available = 0
                    )''', (target_date,))
        
        available = [{'id': row[0], 'name': row[1]} for row in c.fetchall()]
        conn.close()
        return available
    
    def get_person_skills(self, person_id):
        conn = sqlite3.connect(self.database)
        c = conn.cursor()
        
        c.execute('''SELECT m.id, m.name, s.skill_level 
                    FROM skills s
                    JOIN machines m ON s.machine_id = m.id
                    WHERE s.person_id = ?''', (person_id,))
        
        skills = {row[0]: {'name': row[1], 'level': row[2]} for row in c.fetchall()}
        conn.close()
        return skills
    
    def get_pending_jobs(self, end_date):
        conn = sqlite3.connect(self.database)
        c = conn.cursor()
        
        c.execute('''SELECT id, project_name, quantity, completed_quantity,
                           due_date, priority, precision_required, 
                           machine_sequence, estimated_hours, sequential
                    FROM jobs 
                    WHERE status != 'completed' AND due_date <= ?
                    ORDER BY priority DESC, due_date ASC''', (end_date,))
        
        jobs = []
        for row in c.fetchall():
            quantity = row[2] if row[2] is not None else 0
            completed_quantity = row[3] if row[3] is not None else 0
            remaining_quantity = quantity - completed_quantity
            if remaining_quantity > 0:
                jobs.append({
                    'id': row[0],
                    'name': row[1],
                    'remaining_quantity': remaining_quantity,
                    'due_date': datetime.strptime(row[4], '%Y-%m-%d').date() if row[4] else None,
                    'priority': row[5],
                    'precision_required': bool(row[6]),
                    'machine_sequence': row[7] if row[7] else '',
                    'estimated_hours': row[8] or 8.0,
                    'sequential': bool(row[9]) if len(row) > 9 else False
                })
        
        conn.close()
        return jobs
    
    def get_machine_info(self):
        conn = sqlite3.connect(self.database)
        c = conn.cursor()
        
        # Try to get min_operators, fallback to 1 if column doesn't exist
        try:
            c.execute("SELECT id, name, max_operators, base_throughput, min_operators FROM machines")
            machines = {}
            for row in c.fetchall():
                machines[row[0]] = {
                    'name': row[1],
                    'max_operators': row[2],
                    'base_throughput': row[3],
                    'min_operators': row[4] if len(row) > 4 else 1
                }
        except:
            # Fallback for older database schema
            c.execute("SELECT id, name, max_operators, base_throughput FROM machines")
            machines = {row[0]: {
                'name': row[1],
                'max_operators': row[2],
                'base_throughput': row[3],
                'min_operators': 1
            } for row in c.fetchall()}
        
        conn.close()
        return machines
    
    def calculate_job_time(self, job, person_skill_level, machine_throughput):
        base_hours = job['estimated_hours']
        
        skill_multiplier = {
            1: 2.0,
            2: 1.5,
            3: 1.0,
            4: 0.8,
            5: 0.6
        }.get(person_skill_level, 1.0)
        
        adjusted_hours = base_hours * skill_multiplier
        
        if job['remaining_quantity'] < 100:
            adjusted_hours *= 0.8
        
        return min(adjusted_hours, self.shift_duration.total_seconds() / 3600)
    
    def find_best_person_for_job(self, job, machine_id, available_people, current_assignments):
        candidates = []
        
        for person in available_people:
            if person['id'] in current_assignments:
                continue
                
            skills = self.get_person_skills(person['id'])
            
            if machine_id not in skills:
                continue
            
            skill_level = skills[machine_id]['level']
            
            if job['precision_required'] and skill_level < 4:
                continue
            
            score = skill_level
            
            if job['priority'] > 0:
                score += 2
            
            candidates.append((score, person['id'], skill_level))
        
        if not candidates:
            return None
        
        candidates.sort(reverse=True)
        return {
            'person_id': candidates[0][1],
            'skill_level': candidates[0][2]
        }
    
    def generate_schedule(self, start_date, end_date):
        assignments = []
        machines = self.get_machine_info()
        
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() < 5:
                daily_assignments = self.schedule_day(current_date, machines)
                assignments.extend(daily_assignments)
            
            current_date += timedelta(days=1)
        
        return assignments
    
    def schedule_day(self, schedule_date, machines):
        assignments = []
        available_people = self.get_available_people(schedule_date)
        jobs = self.get_pending_jobs(schedule_date + timedelta(days=7))
        
        # Return empty if no people, machines, or jobs
        if not available_people or not machines or not jobs:
            print(f"Skipping {schedule_date}: People={len(available_people)}, Machines={len(machines)}, Jobs={len(jobs)}")
            return assignments
        
        # Track assignments per machine (respecting max_operators)
        machine_assignments = defaultdict(list)  # machine_id -> list of current assignments
        assigned_people = set()
        
        # First pass: Analyze job requirements and machine needs
        job_machine_map = defaultdict(list)  # job_id -> list of (machine_id, machine_name)
        machines_needed_today = set()
        
        for job in jobs:
            if not job['machine_sequence']:
                continue
                
            for machine_name in job['machine_sequence']:
                for m_id, m_info in machines.items():
                    if m_info['name'] == machine_name:
                        job_machine_map[job['id']].append((m_id, machine_name))
                        machines_needed_today.add(m_id)
                        break
        
        # Check if any job has high priority
        has_high_priority = any(job['priority'] > 0 for job in jobs)
        
        # Get minimum operators for each machine (from database)
        machine_min_requirements = {}
        for m_id in machines_needed_today:
            machine_min_requirements[m_id] = machines[m_id].get('min_operators', 1)
        
        # Track how many operators are assigned to each machine
        machine_operator_count = {m_id: 0 for m_id in machines_needed_today}
        
        # Phase 1: Assign minimum operators per machine (unless overridden by high priority)
        for job in jobs:
            if job['id'] not in job_machine_map:
                continue
                
            for machine_id, machine_name in job_machine_map[job['id']]:
                # Get minimum requirement for this machine
                min_required = machine_min_requirements.get(machine_id, 1)
                
                # Override minimum if job has high priority
                if job['priority'] > 0 and has_high_priority:
                    min_required = 0  # Allow all operators to go to high priority work
                
                # Skip if this machine already has minimum coverage
                if machine_operator_count.get(machine_id, 0) >= min_required:
                    continue
                    
                machine_info = machines[machine_id]
                
                # Find best available person for this job/machine
                best_person = self.find_best_person_for_job(
                    job, machine_id, available_people, assigned_people
                )
                
                if not best_person:
                    continue
                
                # Calculate job time
                job_hours = self.calculate_job_time(
                    job, best_person['skill_level'], machine_info['base_throughput']
                )
                
                start_time_td = self.shift_start
                end_time_td = start_time_td + timedelta(hours=job_hours)
                
                # Check if it fits in the shift
                if end_time_td > self.shift_end:
                    end_time_td = self.shift_end
                
                # Create assignment
                assignment = {
                    'date': schedule_date.isoformat(),
                    'machine_id': machine_id,
                    'person_id': best_person['person_id'],
                    'job_id': job['id'],
                    'start_time': self.timedelta_to_time(start_time_td),
                    'end_time': self.timedelta_to_time(end_time_td),
                    'start_time_td': start_time_td,
                    'end_time_td': end_time_td
                }
                
                assignments.append({
                    'date': assignment['date'],
                    'machine_id': assignment['machine_id'],
                    'person_id': assignment['person_id'],
                    'job_id': assignment['job_id'],
                    'start_time': assignment['start_time'],
                    'end_time': assignment['end_time']
                })
                
                assigned_people.add(best_person['person_id'])
                machine_assignments[machine_id].append(assignment)
                machine_operator_count[machine_id] = machine_operator_count.get(machine_id, 0) + 1
        
        # Phase 2: Assign additional operators where beneficial (up to max_operators)
        # First ensure all machines have their minimum, then add more
        for job in jobs:
            if job['id'] not in job_machine_map:
                continue
                
            # Sort by priority - high priority jobs get additional operators first
            job_priority = job.get('priority', 0)
                
            for machine_id, machine_name in job_machine_map[job['id']]:
                machine_info = machines[machine_id]
                max_operators = machine_info['max_operators']
                min_operators = machine_info.get('min_operators', 1)
                
                # Check how many operators are currently assigned
                current_operators = len(machine_assignments[machine_id])
                
                # Calculate how many more we can assign
                additional_operators = min(
                    max_operators - current_operators,
                    len(available_people) - len(assigned_people)
                )
                
                # Assign additional operators if available and beneficial
                for i in range(additional_operators):
                    best_person = self.find_best_person_for_job(
                        job, machine_id, available_people, assigned_people
                    )
                    
                    if not best_person:
                        break
                    
                    # Calculate job time (same as first operator for parallel work)
                    job_hours = self.calculate_job_time(
                        job, best_person['skill_level'], machine_info['base_throughput']
                    )
                    
                    # Parallel work - same time slot as other operators
                    start_time_td = self.shift_start
                    end_time_td = start_time_td + timedelta(hours=job_hours / (current_operators + 1))
                    
                    if end_time_td > self.shift_end:
                        end_time_td = self.shift_end
                    
                    # Create assignment
                    assignment = {
                        'date': schedule_date.isoformat(),
                        'machine_id': machine_id,
                        'person_id': best_person['person_id'],
                        'job_id': job['id'],
                        'start_time': self.timedelta_to_time(start_time_td),
                        'end_time': self.timedelta_to_time(end_time_td),
                        'start_time_td': start_time_td,
                        'end_time_td': end_time_td
                    }
                    
                    assignments.append({
                        'date': assignment['date'],
                        'machine_id': assignment['machine_id'],
                        'person_id': assignment['person_id'],
                        'job_id': assignment['job_id'],
                        'start_time': assignment['start_time'],
                        'end_time': assignment['end_time']
                    })
                    
                    assigned_people.add(best_person['person_id'])
                    machine_assignments[machine_id].append(assignment)
        
        return assignments
    
    def timedelta_to_time(self, td):
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"