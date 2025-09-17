from flask import Flask, render_template, request, jsonify, send_file, redirect
import sqlite3
import json
from datetime import datetime, timedelta, date
import os
from scheduling_algorithm import SchedulingAlgorithm
from simple_scheduling_algorithm import SimpleSchedulingAlgorithm
import csv

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

DATABASE = 'shift_planner.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS people (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS machines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    max_operators INTEGER DEFAULT 1,
                    base_throughput REAL DEFAULT 100
                )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id INTEGER,
                    machine_id INTEGER,
                    skill_level INTEGER,
                    FOREIGN KEY(person_id) REFERENCES people(id),
                    FOREIGN KEY(machine_id) REFERENCES machines(id),
                    UNIQUE(person_id, machine_id)
                )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS job_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_code TEXT UNIQUE,
                    name TEXT NOT NULL,
                    machine_sequence TEXT,
                    estimated_hours REAL,
                    precision_required BOOLEAN DEFAULT 0
                )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_name TEXT NOT NULL,
                    template_id INTEGER,
                    quantity INTEGER,
                    due_date DATE,
                    priority INTEGER DEFAULT 0,
                    precision_required BOOLEAN DEFAULT 0,
                    machine_sequence TEXT,
                    estimated_hours REAL,
                    completed_quantity INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(template_id) REFERENCES job_templates(id)
                )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS availability (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id INTEGER,
                    date DATE,
                    available BOOLEAN DEFAULT 1,
                    reason TEXT,
                    FOREIGN KEY(person_id) REFERENCES people(id),
                    UNIQUE(person_id, date)
                )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS schedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE,
                    machine_id INTEGER,
                    person_id INTEGER,
                    job_id INTEGER,
                    start_time TIME,
                    end_time TIME,
                    FOREIGN KEY(machine_id) REFERENCES machines(id),
                    FOREIGN KEY(person_id) REFERENCES people(id),
                    FOREIGN KEY(job_id) REFERENCES jobs(id)
                )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS job_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER,
                    machine_id INTEGER,
                    completed_quantity INTEGER,
                    remaining_hours REAL,
                    date DATE,
                    FOREIGN KEY(job_id) REFERENCES jobs(id),
                    FOREIGN KEY(machine_id) REFERENCES machines(id)
                )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS disabled_machines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    machine_id INTEGER,
                    date DATE,
                    FOREIGN KEY(machine_id) REFERENCES machines(id),
                    UNIQUE(machine_id, date)
                )''')
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return redirect('/schedule')

@app.route('/schedule')
def schedule():
    return render_template('schedule.html', active_page='schedule')

@app.route('/jobs')
def jobs():
    return render_template('jobs.html', active_page='jobs')

@app.route('/people')
def people():
    return render_template('people.html', active_page='people')

@app.route('/machines')
def machines():
    return render_template('machines.html', active_page='machines')

@app.route('/templates')
def templates():
    return render_template('templates.html', active_page='templates')

@app.route('/availability')
def availability():
    return render_template('availability.html', active_page='availability')

@app.route('/reports')
def reports():
    return render_template('reports.html', active_page='reports')

@app.route('/api/people', methods=['GET', 'POST', 'DELETE'])
@app.route('/api/people/<int:person_id>', methods=['PUT'])
def manage_people(person_id=None):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute('''SELECT p.id, p.name, 
                     GROUP_CONCAT(m.name || ':' || s.skill_level) as skills
                     FROM people p
                     LEFT JOIN skills s ON p.id = s.person_id
                     LEFT JOIN machines m ON s.machine_id = m.id
                     GROUP BY p.id''')
        people = []
        for row in c.fetchall():
            person = {
                'id': row[0],
                'name': row[1],
                'skills': {}
            }
            if row[2]:
                for skill in row[2].split(','):
                    if ':' in skill:
                        machine, level = skill.split(':')
                        person['skills'][machine] = int(level)
            people.append(person)
        conn.close()
        return jsonify(people)
    
    elif request.method == 'POST':
        data = request.json
        c.execute("INSERT INTO people (name) VALUES (?)", (data['name'],))
        person_id = c.lastrowid
        
        if 'skills' in data:
            for machine_name, skill_level in data['skills'].items():
                c.execute("SELECT id FROM machines WHERE name = ?", (machine_name,))
                machine_row = c.fetchone()
                if machine_row:
                    c.execute("INSERT OR REPLACE INTO skills (person_id, machine_id, skill_level) VALUES (?, ?, ?)",
                             (person_id, machine_row[0], skill_level))
        
        conn.commit()
        conn.close()
        return jsonify({'id': person_id, 'status': 'success'})
    
    elif request.method == 'PUT':
        data = request.json
        # Update person name
        c.execute("UPDATE people SET name = ? WHERE id = ?", (data['name'], person_id))
        
        # Delete existing skills
        c.execute("DELETE FROM skills WHERE person_id = ?", (person_id,))
        
        # Insert new skills
        if 'skills' in data:
            for machine_name, skill_level in data['skills'].items():
                c.execute("SELECT id FROM machines WHERE name = ?", (machine_name,))
                machine_row = c.fetchone()
                if machine_row:
                    c.execute("INSERT INTO skills (person_id, machine_id, skill_level) VALUES (?, ?, ?)",
                             (person_id, machine_row[0], skill_level))
        
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    
    elif request.method == 'DELETE':
        person_id = request.json['id']
        c.execute("DELETE FROM skills WHERE person_id = ?", (person_id,))
        c.execute("DELETE FROM availability WHERE person_id = ?", (person_id,))
        c.execute("DELETE FROM people WHERE id = ?", (person_id,))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})

@app.route('/api/machines', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_machines():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT id, name, max_operators, base_throughput, min_operators FROM machines")
        machines = []
        for row in c.fetchall():
            machines.append({
                'id': row[0], 
                'name': row[1], 
                'max_operators': row[2], 
                'base_throughput': row[3],
                'min_operators': row[4] if len(row) > 4 else 1
            })
        conn.close()
        return jsonify(machines)
    
    elif request.method == 'POST':
        data = request.json
        c.execute("INSERT INTO machines (name, max_operators, base_throughput, min_operators) VALUES (?, ?, ?, ?)",
                 (data['name'], data.get('max_operators', 1), data.get('base_throughput', 100), 
                  data.get('min_operators', 1)))
        machine_id = c.lastrowid
        conn.commit()
        conn.close()
        return jsonify({'id': machine_id, 'status': 'success'})
    
    elif request.method == 'PUT':
        data = request.json
        c.execute("""UPDATE machines 
                    SET name = ?, min_operators = ?, max_operators = ?, base_throughput = ?
                    WHERE id = ?""",
                 (data['name'], data.get('min_operators', 1), data.get('max_operators', 1), 
                  data.get('base_throughput', 100), data['id']))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    
    elif request.method == 'DELETE':
        machine_id = request.json['id']
        c.execute("DELETE FROM skills WHERE machine_id = ?", (machine_id,))
        c.execute("DELETE FROM machines WHERE id = ?", (machine_id,))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})

@app.route('/api/job_templates', methods=['GET', 'POST'])
def manage_templates():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM job_templates")
        templates = [{'id': row[0], 'code': row[1], 'name': row[2], 
                     'machine_sequence': row[3], 'estimated_hours': row[4],
                     'precision_required': bool(row[5])} for row in c.fetchall()]
        conn.close()
        return jsonify(templates)
    
    elif request.method == 'POST':
        data = request.json
        c.execute('''INSERT INTO job_templates 
                    (template_code, name, machine_sequence, estimated_hours, precision_required) 
                    VALUES (?, ?, ?, ?, ?)''',
                 (data['code'], data['name'], data['machine_sequence'], 
                  data['estimated_hours'], data.get('precision_required', False)))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})

@app.route('/api/jobs', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_jobs():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute('''SELECT j.*, jt.name as template_name 
                    FROM jobs j 
                    LEFT JOIN job_templates jt ON j.template_id = jt.id
                    WHERE j.status != 'completed'
                    ORDER BY j.priority DESC, j.due_date ASC''')
        jobs = []
        for row in c.fetchall():
            job = {
                'id': row[0],
                'project_name': row[1],
                'template_id': row[2],
                'quantity': row[3],
                'due_date': row[4],
                'priority': row[5],
                'precision_required': bool(row[6]),
                'machine_sequence': row[7],
                'estimated_hours': row[8],
                'completed_quantity': row[9],
                'status': row[10],
                'template_name': row[12] if len(row) > 12 else None
            }
            jobs.append(job)
        conn.close()
        return jsonify(jobs)
    
    elif request.method == 'POST':
        data = request.json
        
        if data.get('template_id'):
            c.execute("SELECT * FROM job_templates WHERE id = ?", (data['template_id'],))
            template = c.fetchone()
            if template:
                machine_sequence = template[3]
                estimated_hours = template[4]
                precision_required = template[5]
            else:
                machine_sequence = data.get('machine_sequence', '')
                estimated_hours = data.get('estimated_hours', 0)
                precision_required = data.get('precision_required', False)
        else:
            machine_sequence = data.get('machine_sequence', '')
            estimated_hours = data.get('estimated_hours', 0)
            precision_required = data.get('precision_required', False)
        
        c.execute('''INSERT INTO jobs 
                    (project_name, template_id, quantity, due_date, priority, 
                     precision_required, machine_sequence, estimated_hours, sequential) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                 (data['project_name'], data.get('template_id'), data['quantity'],
                  data['due_date'], data.get('priority', 0), precision_required,
                  machine_sequence, estimated_hours, data.get('sequential', 0)))
        
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    
    elif request.method == 'PUT':
        data = request.json
        job_id = data['id']
        c.execute('''UPDATE jobs 
                    SET project_name = ?, 
                        template_id = ?,
                        quantity = ?, 
                        due_date = ?,
                        priority = ?,
                        precision_required = ?,
                        machine_sequence = ?,
                        estimated_hours = ?,
                        completed_quantity = ?, 
                        status = ?
                    WHERE id = ?''',
                 (data['project_name'], 
                  data.get('template_id'),
                  data['quantity'],
                  data['due_date'],
                  data.get('priority', 0),
                  1 if data.get('precision_required') else 0,
                  data.get('machine_sequence', ''),
                  data.get('estimated_hours'),
                  data.get('completed_quantity', 0), 
                  data.get('status', 'pending'), 
                  job_id))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    
    elif request.method == 'DELETE':
        job_id = request.json['id']
        c.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})

@app.route('/api/availability', methods=['GET', 'POST'])
def manage_availability():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    if request.method == 'GET':
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        c.execute('''SELECT a.*, p.name 
                    FROM availability a
                    JOIN people p ON a.person_id = p.id
                    WHERE a.date BETWEEN ? AND ? AND a.available = 0''',
                 (start_date, end_date))
        
        unavailable = []
        for row in c.fetchall():
            unavailable.append({
                'person_id': row[1],
                'person_name': row[5],
                'date': row[2],
                'reason': row[4]
            })
        
        conn.close()
        return jsonify(unavailable)
    
    elif request.method == 'POST':
        data = request.json
        c.execute('''INSERT OR REPLACE INTO availability 
                    (person_id, date, available, reason) 
                    VALUES (?, ?, ?, ?)''',
                 (data['person_id'], data['date'], 
                  data.get('available', 0), data.get('reason', 'Vacation')))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})

@app.route('/api/schedule', methods=['GET', 'POST', 'DELETE'])
def manage_schedule():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    if request.method == 'GET':
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date and end_date:
            print(f"Fetching schedule from {start_date} to {end_date}")
            
            c.execute('''SELECT s.*, m.name as machine_name, p.name as person_name,
                               j.project_name
                        FROM schedule s
                        JOIN machines m ON s.machine_id = m.id
                        JOIN people p ON s.person_id = p.id
                        LEFT JOIN jobs j ON s.job_id = j.id
                        WHERE s.date BETWEEN ? AND ?
                        ORDER BY s.date, m.name, s.start_time''',
                     (start_date, end_date))
        else:
            # Return all schedules if no date range specified
            print("Fetching all schedules")
            
            c.execute('''SELECT s.*, m.name as machine_name, p.name as person_name,
                               j.project_name
                        FROM schedule s
                        JOIN machines m ON s.machine_id = m.id
                        JOIN people p ON s.person_id = p.id
                        LEFT JOIN jobs j ON s.job_id = j.id
                        ORDER BY s.date, m.name, s.start_time''')
        
        schedule = []
        for row in c.fetchall():
            schedule.append({
                'id': row[0],
                'date': row[1],
                'machine_id': row[2],
                'machine_name': row[7],
                'person_id': row[3],
                'person_name': row[8],
                'job_id': row[4],
                'job_name': row[9],
                'start_time': row[5],
                'end_time': row[6]
            })
        
        print(f"Found {len(schedule)} schedule entries")
        conn.close()
        return jsonify(schedule)
    
    elif request.method == 'POST':
        data = request.json
        
        c.execute("DELETE FROM schedule WHERE date BETWEEN ? AND ?",
                 (data['start_date'], data['end_date']))
        
        for assignment in data['assignments']:
            c.execute('''INSERT INTO schedule 
                        (date, machine_id, person_id, job_id, start_time, end_time)
                        VALUES (?, ?, ?, ?, ?, ?)''',
                     (assignment['date'], assignment['machine_id'],
                      assignment['person_id'], assignment['job_id'],
                      assignment['start_time'], assignment['end_time']))
        
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    
    elif request.method == 'DELETE':
        data = request.json
        
        c.execute("DELETE FROM schedule WHERE date BETWEEN ? AND ?",
                 (data['start_date'], data['end_date']))
        
        deleted_count = c.rowcount
        conn.commit()
        conn.close()
        
        return jsonify({'status': 'success', 'deleted': deleted_count})

@app.route('/api/generate_schedule', methods=['POST'])
def generate_schedule():
    data = request.json
    start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
    end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
    regenerate = data.get('regenerate', False)  # Option to fully regenerate
    
    print(f"Generating schedule from {start_date} to {end_date} (regenerate={regenerate})")
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Check if schedule already exists for this period
    c.execute("SELECT COUNT(*) FROM schedule WHERE date BETWEEN ? AND ?",
             (start_date, end_date))
    existing_count = c.fetchone()[0]
    
    if existing_count > 0 and not regenerate:
        print(f"Schedule already exists with {existing_count} assignments")
        conn.close()
        return jsonify({'status': 'success', 'assignments': [], 
                       'message': f'Schedule already exists with {existing_count} assignments'})
    
    # Clear existing schedule if regenerating BEFORE generating new one
    if regenerate and existing_count > 0:
        print(f"Clearing {existing_count} existing assignments for regeneration")
        c.execute("DELETE FROM schedule WHERE date BETWEEN ? AND ?",
                 (start_date, end_date))
        conn.commit()
    
    # Use the simple algorithm without time/throughput calculations
    scheduler = SimpleSchedulingAlgorithm(DATABASE)
    assignments = scheduler.generate_schedule(start_date, end_date)
    
    print(f"Generated {len(assignments)} assignments")
    
    # Check current data
    c.execute("SELECT COUNT(*) FROM people")
    people_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM machines")
    machines_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM jobs WHERE status != 'completed'")
    jobs_count = c.fetchone()[0]
    
    print(f"Database contains: {people_count} people, {machines_count} machines, {jobs_count} pending jobs")
    
    # Insert new assignments
    for assignment in assignments:
        # Check if assignment already exists
        c.execute('''SELECT id FROM schedule 
                    WHERE date = ? AND machine_id = ? AND person_id = ? AND job_id = ?''',
                 (assignment['date'], assignment['machine_id'],
                  assignment['person_id'], assignment['job_id']))
        
        if not c.fetchone():  # Only insert if not exists
            c.execute('''INSERT INTO schedule 
                        (date, machine_id, person_id, job_id, start_time, end_time)
                        VALUES (?, ?, ?, ?, ?, ?)''',
                     (assignment['date'], assignment['machine_id'],
                      assignment['person_id'], assignment['job_id'],
                      assignment['start_time'], assignment['end_time']))
    
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success', 'assignments': assignments, 
                   'message': f'Generated {len(assignments)} assignments'})

@app.route('/api/update_progress', methods=['POST'])
def update_progress():
    data = request.json
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    job_id = data['job_id']
    machine_id = data['machine_id']
    completed_for_machine = data['completed_quantity']
    
    # First, update or insert progress for this specific machine
    c.execute('''SELECT id FROM job_progress 
                WHERE job_id = ? AND machine_id = ?''',
             (job_id, machine_id))
    existing = c.fetchone()
    
    if existing:
        # Update existing progress for this machine
        c.execute('''UPDATE job_progress 
                    SET completed_quantity = ?, remaining_hours = ?, date = ?
                    WHERE job_id = ? AND machine_id = ?''',
                 (completed_for_machine, data.get('remaining_hours', 0), 
                  data['date'], job_id, machine_id))
    else:
        # Insert new progress for this machine
        c.execute('''INSERT INTO job_progress 
                    (job_id, machine_id, completed_quantity, remaining_hours, date)
                    VALUES (?, ?, ?, ?, ?)''',
                 (job_id, machine_id, completed_for_machine,
                  data.get('remaining_hours', 0), data['date']))
    
    # Check if job should be marked complete for this machine
    c.execute("SELECT quantity, machine_sequence FROM jobs WHERE id = ?", (job_id,))
    job_info = c.fetchone()
    total_quantity = job_info[0]
    machine_sequence = job_info[1]
    
    # Count how many machines have completed their work
    if machine_sequence:
        machines_in_sequence = [m.strip() for m in machine_sequence.split(',')]
        
        # Get machine IDs for all machines in sequence
        machine_ids = []
        for machine_name in machines_in_sequence:
            c.execute("SELECT id FROM machines WHERE name = ?", (machine_name,))
            m_id = c.fetchone()
            if m_id:
                machine_ids.append(m_id[0])
        
        # Check completion status for each machine
        machines_completed = 0
        for m_id in machine_ids:
            c.execute('''SELECT completed_quantity FROM job_progress 
                        WHERE job_id = ? AND machine_id = ?''',
                     (job_id, m_id))
            progress = c.fetchone()
            if progress and progress[0] >= total_quantity:
                machines_completed += 1
        
        # Update job status based on overall progress
        if machines_completed == len(machine_ids):
            # All machines completed - job is done
            c.execute('''UPDATE jobs 
                        SET status = 'completed', completed_quantity = ?
                        WHERE id = ?''',
                     (total_quantity, job_id))
        else:
            # Some machines still working
            c.execute('''UPDATE jobs 
                        SET status = 'in_progress'
                        WHERE id = ?''',
                     (job_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success'})

@app.route('/api/export_schedule')
def export_schedule():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    c.execute('''SELECT s.date, m.name as machine, p.name as person,
                       j.project_name as job, s.start_time, s.end_time
                FROM schedule s
                JOIN machines m ON s.machine_id = m.id
                JOIN people p ON s.person_id = p.id
                LEFT JOIN jobs j ON s.job_id = j.id
                WHERE s.date BETWEEN ? AND ?
                ORDER BY s.date, m.name, s.start_time''',
             (start_date, end_date))
    
    rows = c.fetchall()
    conn.close()
    
    filename = f"schedule_{start_date}_to_{end_date}.csv"
    filepath = os.path.join('exports', filename)
    
    with open(filepath, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Date', 'Machine', 'Person', 'Job', 'Start Time', 'End Time'])
        writer.writerows(rows)
    
    return send_file(filepath, as_attachment=True)

@app.route('/api/disabled_machines', methods=['GET', 'POST', 'DELETE'])
def disabled_machines():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute('''SELECT dm.machine_id, dm.date, m.name
                    FROM disabled_machines dm
                    JOIN machines m ON dm.machine_id = m.id''')
        
        disabled = []
        for row in c.fetchall():
            disabled.append({
                'machine_id': row[0],
                'date': row[1],
                'machine_name': row[2]
            })
        
        conn.close()
        return jsonify(disabled)
    
    elif request.method == 'POST':
        data = request.json
        machine_id = data['machine_id']
        date = data['date']
        
        try:
            c.execute('INSERT INTO disabled_machines (machine_id, date) VALUES (?, ?)',
                     (machine_id, date))
            conn.commit()
            conn.close()
            return jsonify({'status': 'success', 'message': 'Machine disabled for date'})
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'status': 'error', 'message': 'Machine already disabled for this date'}), 400
    
    elif request.method == 'DELETE':
        data = request.json
        machine_id = data['machine_id']
        date = data['date']
        
        c.execute('DELETE FROM disabled_machines WHERE machine_id = ? AND date = ?',
                 (machine_id, date))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'message': 'Machine enabled for date'})

@app.route('/database')
def database():
    return render_template('database.html', active_page='database')

@app.route('/api/database/stats')
def database_stats():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    stats = {}
    
    # Get table statistics
    tables = ['people', 'machines', 'jobs', 'schedule', 'job_templates', 'skills', 'availability', 'job_progress', 'disabled_machines']
    for table in tables:
        c.execute(f'SELECT COUNT(*) FROM {table}')
        stats[table] = c.fetchone()[0]
    
    # Get database file size
    stats['file_size'] = os.path.getsize(DATABASE)
    
    # Get orphaned records count
    c.execute('''SELECT COUNT(*) FROM schedule 
                WHERE person_id NOT IN (SELECT id FROM people)
                OR machine_id NOT IN (SELECT id FROM machines)
                OR job_id NOT IN (SELECT id FROM jobs)''')
    stats['orphaned_schedule'] = c.fetchone()[0]
    
    c.execute('''SELECT COUNT(*) FROM skills 
                WHERE person_id NOT IN (SELECT id FROM people)
                OR machine_id NOT IN (SELECT id FROM machines)''')
    stats['orphaned_skills'] = c.fetchone()[0]
    
    conn.close()
    return jsonify(stats)

@app.route('/api/database/backup', methods=['POST'])
def database_backup():
    import shutil
    from datetime import datetime
    
    # Create backup filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = 'backups'
    os.makedirs(backup_dir, exist_ok=True)
    backup_file = os.path.join(backup_dir, f'shift_planner_{timestamp}.db')
    
    try:
        shutil.copy2(DATABASE, backup_file)
        return jsonify({
            'status': 'success',
            'message': f'Database backed up successfully',
            'filename': backup_file
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/database/restore', methods=['POST'])
def database_restore():
    import shutil
    
    data = request.json
    backup_file = data.get('backup_file')
    
    if not backup_file or not os.path.exists(backup_file):
        return jsonify({
            'status': 'error',
            'message': 'Backup file not found'
        }), 400
    
    try:
        # Create a temporary backup of current database
        temp_backup = DATABASE + '.temp'
        shutil.copy2(DATABASE, temp_backup)
        
        # Restore from backup
        shutil.copy2(backup_file, DATABASE)
        
        # Remove temporary backup
        os.remove(temp_backup)
        
        return jsonify({
            'status': 'success',
            'message': 'Database restored successfully'
        })
    except Exception as e:
        # Try to restore from temp backup
        if os.path.exists(DATABASE + '.temp'):
            shutil.copy2(DATABASE + '.temp', DATABASE)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/database/validate', methods=['POST'])
def database_validate():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    issues = []
    
    # Check for orphaned schedule entries
    c.execute('''SELECT id, date, person_id, machine_id, job_id FROM schedule 
                WHERE person_id NOT IN (SELECT id FROM people)
                OR machine_id NOT IN (SELECT id FROM machines)
                OR job_id NOT IN (SELECT id FROM jobs)''')
    orphaned_schedule = c.fetchall()
    if orphaned_schedule:
        issues.append({
            'type': 'orphaned_schedule',
            'count': len(orphaned_schedule),
            'message': f'{len(orphaned_schedule)} orphaned schedule entries found'
        })
    
    # Check for orphaned skills
    c.execute('''SELECT id FROM skills 
                WHERE person_id NOT IN (SELECT id FROM people)
                OR machine_id NOT IN (SELECT id FROM machines)''')
    orphaned_skills = c.fetchall()
    if orphaned_skills:
        issues.append({
            'type': 'orphaned_skills',
            'count': len(orphaned_skills),
            'message': f'{len(orphaned_skills)} orphaned skill entries found'
        })
    
    # Check for duplicate jobs
    c.execute('''SELECT project_name, COUNT(*) as count FROM jobs 
                GROUP BY project_name, machine_sequence, quantity 
                HAVING count > 1''')
    duplicate_jobs = c.fetchall()
    if duplicate_jobs:
        issues.append({
            'type': 'duplicate_jobs',
            'count': sum(row[1] - 1 for row in duplicate_jobs),
            'message': f'{len(duplicate_jobs)} duplicate job groups found'
        })
    
    # Check for jobs with null quantities
    c.execute('SELECT COUNT(*) FROM jobs WHERE quantity IS NULL')
    null_quantities = c.fetchone()[0]
    if null_quantities:
        issues.append({
            'type': 'null_quantities',
            'count': null_quantities,
            'message': f'{null_quantities} jobs with NULL quantity'
        })
    
    conn.close()
    
    return jsonify({
        'status': 'success' if not issues else 'issues_found',
        'issues': issues
    })

@app.route('/api/database/cleanup', methods=['POST'])
def database_cleanup():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    data = request.json
    action = data.get('action')
    
    if action == 'remove_orphaned':
        # Remove orphaned schedule entries
        c.execute('''DELETE FROM schedule 
                    WHERE person_id NOT IN (SELECT id FROM people)
                    OR machine_id NOT IN (SELECT id FROM machines)
                    OR job_id NOT IN (SELECT id FROM jobs)''')
        schedule_deleted = c.rowcount
        
        # Remove orphaned skills
        c.execute('''DELETE FROM skills 
                    WHERE person_id NOT IN (SELECT id FROM people)
                    OR machine_id NOT IN (SELECT id FROM machines)''')
        skills_deleted = c.rowcount
        
        # Remove orphaned job progress
        c.execute('''DELETE FROM job_progress 
                    WHERE job_id NOT IN (SELECT id FROM jobs)
                    OR machine_id NOT IN (SELECT id FROM machines)''')
        progress_deleted = c.rowcount
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': f'Removed {schedule_deleted} orphaned schedule entries, {skills_deleted} orphaned skills, {progress_deleted} orphaned progress entries'
        })
    
    elif action == 'remove_duplicates':
        # Remove duplicate jobs (keep the one with lowest ID)
        c.execute('''DELETE FROM jobs 
                    WHERE id NOT IN (
                        SELECT MIN(id) 
                        FROM jobs 
                        GROUP BY project_name, machine_sequence, quantity
                    )''')
        jobs_deleted = c.rowcount
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': f'Removed {jobs_deleted} duplicate jobs'
        })
    
    elif action == 'fix_null_quantities':
        # Set NULL quantities to 1
        c.execute('UPDATE jobs SET quantity = 1 WHERE quantity IS NULL')
        jobs_updated = c.rowcount
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': f'Fixed {jobs_updated} jobs with NULL quantity'
        })
    
    elif action == 'clear_old_schedule':
        # Clear schedule entries older than 30 days
        cutoff_date = (datetime.now() - timedelta(days=30)).date().isoformat()
        c.execute('DELETE FROM schedule WHERE date < ?', (cutoff_date,))
        deleted = c.rowcount
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': f'Removed {deleted} old schedule entries'
        })
    
    else:
        conn.close()
        return jsonify({
            'status': 'error',
            'message': 'Invalid action'
        }), 400

@app.route('/api/database/export', methods=['GET'])
def database_export():
    import tempfile
    import zipfile
    
    # Create a temporary directory for export files
    with tempfile.TemporaryDirectory() as temp_dir:
        export_dir = os.path.join(temp_dir, 'shift_planner_export')
        os.makedirs(export_dir)
        
        conn = sqlite3.connect(DATABASE)
        
        # Export each table to CSV
        tables = ['people', 'machines', 'jobs', 'schedule', 'job_templates', 'skills', 
                 'availability', 'job_progress', 'disabled_machines']
        
        for table in tables:
            df = sqlite3.connect(DATABASE).execute(f'SELECT * FROM {table}').fetchall()
            if df:
                # Get column names
                cursor = conn.execute(f'SELECT * FROM {table} LIMIT 0')
                columns = [description[0] for description in cursor.description]
                
                # Write to CSV
                csv_file = os.path.join(export_dir, f'{table}.csv')
                with open(csv_file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(columns)
                    writer.writerows(df)
        
        conn.close()
        
        # Create zip file
        zip_file = os.path.join(temp_dir, 'shift_planner_export.zip')
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(export_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, temp_dir)
                    zf.write(file_path, arc_name)
        
        return send_file(zip_file, as_attachment=True, download_name='shift_planner_export.zip')

@app.route('/api/database/clear_all', methods=['POST'])
def database_clear_all():
    data = request.json
    confirm = data.get('confirm')
    
    if confirm != 'DELETE_ALL_DATA':
        return jsonify({
            'status': 'error',
            'message': 'Invalid confirmation'
        }), 400
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Clear all data from tables (but keep structure)
    tables = ['schedule', 'job_progress', 'disabled_machines', 'availability', 
             'skills', 'jobs', 'job_templates', 'machines', 'people']
    
    for table in tables:
        c.execute(f'DELETE FROM {table}')
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'status': 'success',
        'message': 'All data cleared successfully'
    })

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5003)