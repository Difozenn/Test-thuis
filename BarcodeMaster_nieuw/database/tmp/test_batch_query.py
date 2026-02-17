#!/usr/bin/env python3
import sqlite3

db_path = '/mnt/c/Users/Rob_v/Desktop/PP/BarcodeMaster/database/central_logging.sqlite'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

project = "MO06787_Dressing_A_deel2_(5-16)"
print(f"=== Testing Batch Session Query for {project} ===\n")

# Run the updated query
c.execute("""
    SELECT DISTINCT
        s.session_id,
        s.user,
        COALESCE(sp.project, s.project) as project,
        s.start_time,
        s.end_time,
        s.status,
        s.session_type,
        s.work_duration_minutes,
        s.pause_duration_minutes,
        COALESCE(sp.item_count, s.item_count) as item_count,
        sp.item_count as batch_items,
        (SELECT SUM(sp2.item_count) FROM session_projects sp2 WHERE sp2.session_id = s.session_id) as batch_total_items
    FROM sessions s
    LEFT JOIN session_projects sp ON s.session_id = sp.session_id AND sp.project = ?
    WHERE s.project = ?
       OR sp.project = ?
    ORDER BY s.start_time
""", (project, project, project))

sessions = []
for row in c.fetchall():
    session = dict(row)
    
    # For SCANNER batch sessions, calculate proportional work time
    if session['session_type'] == 'SCANNER' and session['batch_items'] and session['batch_total_items']:
        proportion = session['batch_items'] / session['batch_total_items']
        session['allocated_work_minutes'] = session['work_duration_minutes'] * proportion
        session['allocated_pause_minutes'] = (session['pause_duration_minutes'] or 0) * proportion
        print(f"SCANNER Batch Session: {session['session_id']}")
        print(f"  User: {session['user']}")
        print(f"  Total session time: {session['work_duration_minutes']:.2f} min")
        print(f"  Items for this project: {session['batch_items']} / {session['batch_total_items']} total")
        print(f"  Proportion: {proportion:.2%}")
        print(f"  Allocated work time: {session['allocated_work_minutes']:.2f} min")
        print(f"  Allocated pause time: {session['allocated_pause_minutes']:.2f} min")
    else:
        # For non-batch sessions, use full time
        session['allocated_work_minutes'] = session['work_duration_minutes']
        session['allocated_pause_minutes'] = session['pause_duration_minutes'] or 0
        print(f"{session['session_type']} Session: {session['session_id']}")
        print(f"  User: {session['user']}")
        print(f"  Work time: {session['work_duration_minutes']:.2f} min")
    
    sessions.append(session)
    print()

# Calculate totals
total_allocated_work = sum(s['allocated_work_minutes'] or 0 for s in sessions)
total_allocated_pause = sum(s['allocated_pause_minutes'] or 0 for s in sessions)

print(f"Total Allocated Work Time: {total_allocated_work:.2f} min")
print(f"Total Allocated Pause Time: {total_allocated_pause:.2f} min")

# Get project session data
c.execute("""
    SELECT total_duration_minutes
    FROM project_sessions
    WHERE project = ?
    AND DATE(start_time) = DATE('now')
""", (project,))

ps = c.fetchone()
if ps:
    project_time = ps['total_duration_minutes']
    idle_time = project_time - total_allocated_work
    idle_percent = (idle_time / project_time * 100) if project_time > 0 else 0
    
    print(f"\nProject Time: {project_time:.2f} min")
    print(f"Idle Time: {idle_time:.2f} min ({idle_percent:.1f}% of project time)")
    print(f"  Expected: ~32 min based on proportional allocation")

conn.close()