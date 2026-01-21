#!/usr/bin/env python3
"""
Fix project_sessions for projects worked on in multiple batch sessions
For display purposes, we'll update the single entry to have the TOTAL proportional time
"""
import sqlite3

db_path = '/mnt/c/Users/Rob_v/Desktop/PP/BarcodeMaster/database/central_logging.sqlite'
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("=== Fixing Project Sessions for Multiple Batch Work ===\n")

projects = ['MO06787_Dressing_A_deel2_(5-16)', 'MO06797_Bureaukast_(15-16)']

for project in projects:
    print(f"Processing {project}:")
    
    # Get all batch sessions that included this project
    c.execute("""
        SELECT 
            s.session_id,
            s.work_duration_minutes,
            s.pause_duration_minutes,
            sp.item_count,
            (SELECT SUM(item_count) FROM session_projects WHERE session_id = s.session_id) as total_items
        FROM sessions s
        JOIN session_projects sp ON s.session_id = sp.session_id
        WHERE sp.project = ?
        AND s.session_type = 'SCANNER'
        ORDER BY s.start_time
    """, (project,))
    
    sessions = c.fetchall()
    total_proportional_time = 0
    
    for session in sessions:
        session_id = session[0]
        work_minutes = session[1] or 0
        pause_minutes = session[2] or 0
        item_count = session[3]
        total_items = session[4]
        
        if total_items > 0:
            proportion = item_count / total_items
            session_total = work_minutes + pause_minutes
            proportional_time = session_total * proportion
            total_proportional_time += proportional_time
            
            print(f"  Session {session_id[:20]}...")
            print(f"    Items: {item_count}/{total_items} ({proportion:.1%})")
            print(f"    Proportional time: {proportional_time:.1f} min")
    
    print(f"  Total proportional time across all sessions: {total_proportional_time:.1f} min")
    
    # Update the project_sessions entry with the total
    # Get the earliest start and latest end time
    c.execute("""
        SELECT 
            MIN(l.timestamp) as first_log,
            MAX(CASE WHEN l.event = 'AFGEMELD' THEN l.timestamp END) as last_afgemeld
        FROM logs l
        WHERE l.project = ?
    """, (project,))
    
    times = c.fetchone()
    if times and times[0]:
        # Update or create project_sessions with total proportional time
        c.execute("""
            UPDATE project_sessions
            SET total_duration_minutes = ?,
                end_time = COALESCE(?, end_time)
            WHERE project = ?
        """, (total_proportional_time, times[1], project))
        
        if c.rowcount == 0:
            # Create if doesn't exist
            c.execute("""
                INSERT INTO project_sessions (project, start_time, end_time, total_duration_minutes, status)
                VALUES (?, ?, ?, ?, 'completed')
            """, (project, times[0], times[1], total_proportional_time))
        
        print(f"  ✓ Updated project_sessions with total time: {total_proportional_time:.1f} min\n")

conn.commit()

print("\n=== Verification ===\n")

for project in projects:
    c.execute("""
        SELECT total_duration_minutes 
        FROM project_sessions 
        WHERE project = ?
    """, (project,))
    
    result = c.fetchone()
    if result:
        print(f"{project}: {result[0]:.1f} min")

conn.close()
print("\n✓ Done!")