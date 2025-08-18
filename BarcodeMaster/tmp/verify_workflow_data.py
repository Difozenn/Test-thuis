#!/usr/bin/env python3
"""Verify workflow test data was generated correctly"""

import sqlite3
from datetime import datetime

def verify_workflow_data():
    conn = sqlite3.connect('database/central_logging.sqlite')
    cursor = conn.cursor()
    
    print('=== WORKFLOW DATA VERIFICATION ===')
    
    # Check today's data
    today = datetime.now().strftime('%Y-%m-%d')
    
    cursor.execute('SELECT COUNT(*) FROM logs WHERE DATE(timestamp) = ?', (today,))
    todays_events = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM sessions WHERE DATE(start_time) = ? AND status = ?', (today, 'completed'))
    todays_sessions = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT project) FROM sessions WHERE project != ? AND DATE(start_time) = ?', ('', today))
    todays_projects = cursor.fetchone()[0]
    
    print(f'Today ({today}):')
    print(f'  Events: {todays_events}')
    print(f'  Completed sessions: {todays_sessions}')
    print(f'  Projects: {todays_projects}')
    
    # Check session types
    print('\nSession types:')
    cursor.execute('''
        SELECT session_type, COUNT(*) as count
        FROM sessions 
        WHERE status = ?
        GROUP BY session_type
    ''', ('completed',))
    for row in cursor.fetchall():
        print(f'  {row[0]}: {row[1]} sessions')
    
    # Check user efficiency
    print('\nUser efficiency (recent):')
    cursor.execute('''
        SELECT user, COUNT(*) as days, AVG(actual_items_per_hour) as avg_rate
        FROM user_efficiency_history
        WHERE date >= date('now', '-7 days')
        GROUP BY user
        ORDER BY avg_rate DESC
    ''')
    for row in cursor.fetchall():
        print(f'  {row[0]}: {row[1]} days, {row[2]:.1f} items/hour avg')
    
    # Check project sessions
    cursor.execute('SELECT COUNT(*) FROM project_sessions WHERE status = ?', ('completed',))
    completed_projects = cursor.fetchone()[0]
    print(f'\nCompleted project sessions: {completed_projects}')
    
    # Check event types in logs
    print('\nEvent types in logs:')
    cursor.execute('''
        SELECT event, COUNT(*) as count
        FROM logs
        GROUP BY event
        ORDER BY count DESC
    ''')
    for row in cursor.fetchall()[:10]:  # Show top 10
        print(f'  {row[0]}: {row[1]} events')
    
    conn.close()

if __name__ == "__main__":
    verify_workflow_data()