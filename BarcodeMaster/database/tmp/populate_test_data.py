#!/usr/bin/env python3
"""
Script to populate test data for verifying session_projects linking works correctly
"""
import sqlite3
from datetime import datetime, timedelta
import random

db_path = '/mnt/c/Users/Rob_v/Desktop/PP/BarcodeMaster/database/central_logging.sqlite'

def populate_test_data():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Test data configuration
    user = "TEST_USER"
    projects = ["PROJECT_A", "PROJECT_B", "PROJECT_C"]
    session_id = f"{user}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_TEST"
    
    print(f"Creating test SCANNER session: {session_id}")
    
    # Create a SCANNER session (batch work)
    start_time = (datetime.now() - timedelta(hours=2)).isoformat()
    end_time = (datetime.now() - timedelta(minutes=30)).isoformat()
    
    c.execute("""
        INSERT INTO sessions (
            session_id, user, session_type, project, 
            start_time, end_time, status, 
            work_duration_minutes, item_count
        ) VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?)
    """, (
        session_id, user, 'SCANNER',
        start_time, end_time, 'completed',
        90, 0  # Item count will be in session_projects
    ))
    
    print(f"Session created successfully")
    
    # Link projects to the session via session_projects
    total_items = 0
    for i, project in enumerate(projects):
        item_count = random.randint(20, 50)
        total_items += item_count
        
        c.execute("""
            INSERT INTO session_projects (
                session_id, project, added_time, item_count
            ) VALUES (?, ?, ?, ?)
        """, (session_id, project, start_time, item_count))
        
        print(f"  Linked {project}: {item_count} items")
        
        # Also create some log entries for the project
        c.execute("""
            INSERT INTO logs (
                timestamp, event, user, project, item_count, details
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            start_time, 'OPEN', user, project, 0, f'Test project {project}'
        ))
        
        c.execute("""
            INSERT INTO logs (
                timestamp, event, user, project, item_count, details
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            end_time, 'AFGEMELD', user, project, item_count, f'Completed {item_count} items'
        ))
    
    print(f"\nTotal items across all projects: {total_items}")
    
    # Create project_sessions entries
    for project in projects:
        c.execute("""
            INSERT OR REPLACE INTO project_sessions (
                project, start_time, end_time, 
                total_duration_minutes, status, total_items
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            project, start_time, end_time,
            90, 'completed', random.randint(20, 50)
        ))
    
    conn.commit()
    print("\nTest data populated successfully!")
    
    # Verify the linking
    print("\n=== Verification ===")
    c.execute("""
        SELECT s.session_id, s.user, s.session_type, 
               sp.project, sp.item_count
        FROM sessions s
        JOIN session_projects sp ON s.session_id = sp.session_id
        WHERE s.session_id = ?
    """, (session_id,))
    
    for row in c.fetchall():
        print(f"Session: {row[0]}, Project: {row[3]}, Items: {row[4]}")
    
    conn.close()

if __name__ == "__main__":
    populate_test_data()