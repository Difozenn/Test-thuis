import sqlite3
from datetime import datetime, timedelta

DATABASE = 'shift_planner.db'

def init_sample_data():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Check if data already exists
    c.execute("SELECT COUNT(*) FROM people")
    if c.fetchone()[0] > 0:
        print("Database already contains data. Skipping initialization.")
        conn.close()
        return
    
    print("Initializing sample data...")
    
    # Add sample machines
    machines = [
        ('Machine A', 1, 100),
        ('Machine B', 2, 150),
        ('Machine C', 1, 80),
        ('Machine D', 1, 120),
        ('Machine E', 2, 200)
    ]
    
    for name, max_ops, throughput in machines:
        c.execute("INSERT INTO machines (name, max_operators, base_throughput) VALUES (?, ?, ?)",
                 (name, max_ops, throughput))
    
    # Add sample people
    people = [
        'John Smith',
        'Jane Doe',
        'Mike Johnson',
        'Sarah Williams',
        'Tom Brown',
        'Emily Davis',
        'Chris Wilson',
        'Lisa Anderson'
    ]
    
    for person_name in people:
        c.execute("INSERT INTO people (name) VALUES (?)", (person_name,))
        person_id = c.lastrowid
        
        # Add random skills for each person
        c.execute("SELECT id FROM machines")
        machine_ids = c.fetchall()
        
        import random
        for machine_id in machine_ids:
            if random.random() > 0.3:  # 70% chance of having skill
                skill_level = random.randint(1, 5)
                c.execute("INSERT INTO skills (person_id, machine_id, skill_level) VALUES (?, ?, ?)",
                         (person_id, machine_id[0], skill_level))
    
    # Add sample job templates
    templates = [
        ('101', 'Standard Widget', 'Machine A,Machine B,Machine C', 6.0, False),
        ('102', 'Premium Widget', 'Machine A,Machine C,Machine D', 8.0, True),
        ('103', 'Basic Component', 'Machine B,Machine E', 4.0, False),
        ('104', 'Complex Assembly', 'Machine A,Machine B,Machine C,Machine D', 12.0, True)
    ]
    
    for code, name, sequence, hours, precision in templates:
        c.execute('''INSERT INTO job_templates 
                    (template_code, name, machine_sequence, estimated_hours, precision_required) 
                    VALUES (?, ?, ?, ?, ?)''',
                 (code, name, sequence, hours, precision))
    
    # Add sample jobs
    today = datetime.now().date()
    jobs = [
        ('Project Alpha', 1, 500, (today + timedelta(days=3)).isoformat(), 1, False, 'Machine A,Machine B', 8.0),
        ('Project Beta', 2, 300, (today + timedelta(days=5)).isoformat(), 0, True, 'Machine A,Machine C,Machine D', 10.0),
        ('Rush Order X', None, 150, (today + timedelta(days=1)).isoformat(), 1, False, 'Machine B,Machine E', 5.0),
        ('Standard Batch 1', 1, 1000, (today + timedelta(days=7)).isoformat(), 0, False, 'Machine A,Machine B,Machine C', 6.0),
        ('Premium Set A', 2, 200, (today + timedelta(days=4)).isoformat(), 0, True, 'Machine A,Machine C,Machine D', 8.0),
        ('Test Run 1', None, 50, (today + timedelta(days=2)).isoformat(), 0, False, 'Machine E', 2.0)
    ]
    
    for project_name, template_id, quantity, due_date, priority, precision, sequence, hours in jobs:
        c.execute('''INSERT INTO jobs 
                    (project_name, template_id, quantity, due_date, priority, 
                     precision_required, machine_sequence, estimated_hours, completed_quantity, status) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                 (project_name, template_id, quantity, due_date, priority, 
                  precision, sequence, hours, 0, 'pending'))
    
    conn.commit()
    conn.close()
    print("Sample data initialized successfully!")
    print("- Added 5 machines")
    print("- Added 8 people with random skills")
    print("- Added 4 job templates")
    print("- Added 6 sample jobs")

if __name__ == '__main__':
    init_sample_data()