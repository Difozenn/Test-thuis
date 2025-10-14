#!/usr/bin/env python3
"""
Verification script for statistics calculations
Run this to manually verify the Project Time Analysis data
"""

import sqlite3
from datetime import datetime

# Connect to database
conn = sqlite3.connect('central_logging.sqlite')
conn.row_factory = sqlite3.Row
c = conn.cursor()

print("=" * 80)
print("PROJECT TIME ANALYSIS VERIFICATION")
print("=" * 80)
print()

# Get date range for "this year"
year = datetime.now().year
start_date = f"{year}-01-01 00:00:00"
end_date = f"{year}-12-31 23:59:59"

print(f"Date Range: {start_date} to {end_date}")
print()

# 1. Total Project Time (from project_sessions)
print("1. TOTAL PROJECT TIME (from project_sessions)")
print("-" * 80)
c.execute("""
    SELECT
        COUNT(*) as project_count,
        SUM(total_duration_minutes) as total_minutes,
        ROUND(SUM(total_duration_minutes) / 60.0, 1) as total_hours
    FROM project_sessions
    WHERE start_time BETWEEN ? AND ?
""", [start_date, end_date])

project_time = c.fetchone()
print(f"  Projects: {project_time['project_count']}")
print(f"  Total Minutes: {project_time['total_minutes']}")
print(f"  Total Hours: {project_time['total_hours']}h")
print()

# 2. Total Session Time (non-SCANNER)
print("2. TOTAL SESSION TIME (non-SCANNER sessions)")
print("-" * 80)
c.execute("""
    SELECT
        COUNT(*) as session_count,
        SUM(work_duration_minutes) as total_minutes,
        ROUND(SUM(work_duration_minutes) / 60.0, 1) as total_hours
    FROM sessions
    WHERE session_type != 'SCANNER'
    AND start_time BETWEEN ? AND ?
""", [start_date, end_date])

non_scanner_time = c.fetchone()
print(f"  Non-SCANNER Sessions: {non_scanner_time['session_count']}")
print(f"  Total Minutes: {non_scanner_time['total_minutes']}")
print(f"  Total Hours: {non_scanner_time['total_hours']}h")
print()

# 3. Total Session Time (SCANNER - allocated)
print("3. TOTAL SESSION TIME (SCANNER sessions - proportionally allocated)")
print("-" * 80)
c.execute("""
    SELECT
        COUNT(DISTINCT s.session_id) as session_count,
        SUM(
            CASE
                WHEN (SELECT SUM(item_count) FROM session_projects WHERE session_id = s.session_id) > 0 THEN
                    sp.item_count * 1.0 / (SELECT SUM(item_count) FROM session_projects WHERE session_id = s.session_id) * s.work_duration_minutes
                ELSE
                    s.work_duration_minutes / (SELECT COUNT(*) FROM session_projects WHERE session_id = s.session_id)
            END
        ) as total_minutes,
        ROUND(SUM(
            CASE
                WHEN (SELECT SUM(item_count) FROM session_projects WHERE session_id = s.session_id) > 0 THEN
                    sp.item_count * 1.0 / (SELECT SUM(item_count) FROM session_projects WHERE session_id = s.session_id) * s.work_duration_minutes
                ELSE
                    s.work_duration_minutes / (SELECT COUNT(*) FROM session_projects WHERE session_id = s.session_id)
            END
        ) / 60.0, 1) as total_hours
    FROM session_projects sp
    JOIN sessions s ON s.session_id = sp.session_id
    WHERE s.session_type = 'SCANNER'
    AND s.start_time BETWEEN ? AND ?
""", [start_date, end_date])

scanner_time = c.fetchone()
print(f"  SCANNER Sessions: {scanner_time['session_count']}")
print(f"  Total Allocated Minutes: {scanner_time['total_minutes']}")
print(f"  Total Allocated Hours: {scanner_time['total_hours']}h")
print()

# 4. Combined Session Time
print("4. COMBINED SESSION TIME")
print("-" * 80)
total_session_minutes = (non_scanner_time['total_minutes'] or 0) + (scanner_time['total_minutes'] or 0)
total_session_hours = round(total_session_minutes / 60.0, 1)
print(f"  Total Session Minutes: {total_session_minutes}")
print(f"  Total Session Hours: {total_session_hours}h")
print()

# 5. Calculated Idle Time
print("5. CALCULATED IDLE TIME")
print("-" * 80)
idle_minutes = (project_time['total_minutes'] or 0) - total_session_minutes
idle_hours = round(idle_minutes / 60.0, 1)
print(f"  Idle Minutes: {idle_minutes}")
print(f"  Idle Hours: {idle_hours}h")
print()

# 6. Time Efficiency
print("6. TIME EFFICIENCY")
print("-" * 80)
if project_time['total_minutes'] and project_time['total_minutes'] > 0:
    efficiency = round((total_session_minutes * 100.0 / project_time['total_minutes']), 1)
else:
    efficiency = 0
print(f"  Efficiency: {efficiency}%")
print(f"  Formula: ({total_session_minutes} / {project_time['total_minutes']}) * 100")
print()

# 7. Summary
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total Project Time:   {project_time['total_hours']}h ({project_time['total_minutes']} minutes)")
print(f"Total Session Time:   {total_session_hours}h ({total_session_minutes} minutes)")
print(f"Total Idle Time:      {idle_hours}h ({idle_minutes} minutes)")
print(f"Time Efficiency:      {efficiency}%")
print()

# Convert to human readable format
def to_human_time(hours):
    h = int(hours)
    m = int((hours - h) * 60)
    return f"{h}u {m}m"

print("IN HUMAN FORMAT:")
print(f"Total Project Time:   {to_human_time(project_time['total_hours'])}")
print(f"Total Session Time:   {to_human_time(total_session_hours)}")
print(f"Total Idle Time:      {to_human_time(idle_hours)}")
print(f"Time Efficiency:      {efficiency}%")
print()

conn.close()
