#!/usr/bin/env python3
import sqlite3
import sys
import os
from datetime import datetime, timedelta

# Connect to database
db_path = '../database/central_logging.sqlite'
if not os.path.exists(db_path):
    # Try current directory structure
    db_path = 'central_logging.sqlite'
if not os.path.exists(db_path):
    # Try parent
    db_path = '../central_logging.sqlite'

print(f"Using database: {db_path}")
print(f"Database exists: {os.path.exists(db_path)}")
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get a specific user and date range for analysis
user = sys.argv[1] if len(sys.argv) > 1 else "BOERE"  # Default user
days_back = int(sys.argv[2]) if len(sys.argv) > 2 else 30

end_date = datetime.now().strftime('%Y-%m-%d')
start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

print(f"Analyzing data for user: {user}")
print(f"Date range: {start_date} to {end_date}")
print("=" * 80)

# 1. Calculate from SESSIONS table (like calculate_avg_items_per_hour does)
cursor.execute("""
    SELECT
        COUNT(*) as session_count,
        SUM(item_count) as total_items,
        SUM(work_duration_minutes) as total_minutes
    FROM sessions
    WHERE user = ?
    AND status IN ('completed', 'active')
    AND item_count > 0
    AND start_time BETWEEN ? AND ?
""", (user, start_date, end_date + ' 23:59:59'))

sessions_result = cursor.fetchone()
sessions_items = sessions_result['total_items'] or 0
sessions_minutes = sessions_result['total_minutes'] or 0
sessions_count = sessions_result['session_count'] or 0
sessions_avg = (sessions_items / sessions_minutes * 60) if sessions_minutes > 0 else 0

print("SESSIONS TABLE CALCULATION:")
print(f"  Total sessions: {sessions_count}")
print(f"  Total items: {sessions_items}")
print(f"  Total minutes: {sessions_minutes:.1f}")
print(f"  Average: {sessions_avg:.1f} items/hour")
print()

# 2. Get breakdown by session type
cursor.execute("""
    SELECT
        session_type,
        COUNT(*) as count,
        SUM(item_count) as items,
        SUM(work_duration_minutes) as minutes
    FROM sessions
    WHERE user = ?
    AND status IN ('completed', 'active')
    AND item_count > 0
    AND start_time BETWEEN ? AND ?
    GROUP BY session_type
""", (user, start_date, end_date + ' 23:59:59'))

print("BREAKDOWN BY SESSION TYPE:")
for row in cursor.fetchall():
    avg = (row['items'] / row['minutes'] * 60) if row['minutes'] else 0
    print(f"  {row['session_type'] or 'NULL'}: {row['count']} sessions, {row['items']} items, {row['minutes']:.1f} min, {avg:.1f} items/hr")
print()

# 3. Calculate from LOGS table (similar to get_user_activity_date_range)
# Get all projects worked on
cursor.execute("""
    SELECT DISTINCT
        project,
        MAX(item_count) as max_items
    FROM logs
    WHERE user = ?
    AND project IS NOT NULL
    AND project != ''
    AND DATE(timestamp) BETWEEN ? AND ?
    GROUP BY project
""", (user, start_date, end_date))

projects = cursor.fetchall()
logs_total_items = 0
logs_total_minutes = 0

print("LOGS TABLE PROJECT ANALYSIS:")
for proj in projects:
    project = proj['project']
    project_items = proj['max_items'] or 0
    logs_total_items += project_items

    # Get time from sessions for this project
    # First individual sessions
    cursor.execute("""
        SELECT SUM(work_duration_minutes) as minutes
        FROM sessions
        WHERE user = ? AND project = ?
        AND session_type IN ('XLSX_UPDATED', 'MANUAL')
        AND status = 'completed'
        AND DATE(start_time) BETWEEN ? AND ?
    """, (user, project, start_date, end_date))

    individual_minutes = cursor.fetchone()['minutes'] or 0

    # Then batch sessions with proportional allocation
    cursor.execute("""
        SELECT
            s.session_id,
            s.work_duration_minutes,
            sp.item_count as project_items
        FROM sessions s
        JOIN session_projects sp ON s.session_id = sp.session_id
        WHERE s.user = ?
        AND s.session_type = 'SCANNER'
        AND sp.project = ?
        AND s.status = 'completed'
        AND DATE(s.start_time) BETWEEN ? AND ?
    """, (user, project, start_date, end_date))

    batch_minutes = 0
    for batch in cursor.fetchall():
        # Get total items in this batch
        cursor.execute("""
            SELECT SUM(item_count) as batch_total
            FROM session_projects
            WHERE session_id = ?
        """, (batch['session_id'],))
        batch_total = cursor.fetchone()['batch_total'] or 0

        if batch_total > 0 and batch['project_items'] > 0:
            proportion = batch['project_items'] / batch_total
            batch_minutes += batch['work_duration_minutes'] * proportion

    project_minutes = individual_minutes + batch_minutes
    logs_total_minutes += project_minutes

    if project_minutes > 0:
        project_avg = (project_items / project_minutes) * 60
        print(f"  {project}: {project_items} items, {project_minutes:.1f} min ({individual_minutes:.1f} individual + {batch_minutes:.1f} batch), {project_avg:.1f} items/hr")

logs_avg = (logs_total_items / logs_total_minutes * 60) if logs_total_minutes > 0 else 0

print()
print("LOGS TABLE TOTALS:")
print(f"  Total items: {logs_total_items}")
print(f"  Total minutes: {logs_total_minutes:.1f}")
print(f"  Average: {logs_avg:.1f} items/hour")
print()

# 4. Find discrepancies
print("DISCREPANCY ANALYSIS:")
print(f"  Sessions shows: {sessions_avg:.1f} items/hour")
print(f"  Logs shows: {logs_avg:.1f} items/hour")
print(f"  Difference: {sessions_avg - logs_avg:.1f} items/hour ({(sessions_avg/logs_avg - 1)*100:.1f}% higher in sessions)")
print()
print(f"  Items difference: {sessions_items} (sessions) vs {logs_total_items} (logs) = {sessions_items - logs_total_items} items difference")
print(f"  Time difference: {sessions_minutes:.1f} (sessions) vs {logs_total_minutes:.1f} (logs) = {sessions_minutes - logs_total_minutes:.1f} minutes difference")

# 5. Check for sessions without projects
cursor.execute("""
    SELECT COUNT(*) as orphan_count, SUM(item_count) as orphan_items
    FROM sessions
    WHERE user = ?
    AND status = 'completed'
    AND item_count > 0
    AND (project IS NULL OR project = '')
    AND start_time BETWEEN ? AND ?
""", (user, start_date, end_date + ' 23:59:59'))

orphan_result = cursor.fetchone()
if orphan_result['orphan_count'] > 0:
    print()
    print(f"WARNING: Found {orphan_result['orphan_count']} sessions with {orphan_result['orphan_items']} items that have NO PROJECT assigned!")
    print("These appear in sessions calculation but NOT in logs calculation!")

conn.close()