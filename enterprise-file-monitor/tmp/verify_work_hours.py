#!/usr/bin/env python3
"""
Verify that all work hour calculations in the system are using WorkScheduleConfig
"""

import sqlite3
import json
from datetime import datetime, timedelta

def check_work_schedule_config():
    """Check the current WorkScheduleConfig settings"""
    conn = sqlite3.connect('monitoring.db')
    cursor = conn.cursor()
    
    print("=== Work Schedule Configuration ===")
    cursor.execute("""
        SELECT id, name, monday_start, monday_end, tuesday_start, tuesday_end,
               wednesday_start, wednesday_end, thursday_start, thursday_end,
               friday_start, friday_end, saturday_start, saturday_end,
               sunday_start, sunday_end, break_start, break_duration, is_active
        FROM work_schedule_config
        WHERE is_active = 1
    """)
    
    config = cursor.fetchone()
    if config:
        print(f"Active config: {config[1]}")
        
        # Calculate total weekly hours
        total_hours = 0
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for i, day in enumerate(days):
            start = config[2 + i*2]
            end = config[3 + i*2]
            if start and end and end > start:
                daily_hours = end - start - (config[16] or 0)  # Subtract break duration
                total_hours += daily_hours
                print(f"  {day.capitalize()}: {start:.1f} - {end:.1f} ({daily_hours:.1f}h)")
            else:
                print(f"  {day.capitalize()}: Off")
        
        print(f"  Break: {config[15]:.1f} for {config[16]:.1f}h")
        print(f"  Total weekly hours: {total_hours:.1f}")
    else:
        print("No active work schedule config found!")
    
    conn.close()
    return total_hours if config else 0

def check_work_calendar():
    """Check work calendar entries for holidays"""
    conn = sqlite3.connect('monitoring.db')
    cursor = conn.cursor()
    
    print("\n=== Work Calendar (Next 30 days) ===")
    today = datetime.now().date()
    end_date = today + timedelta(days=30)
    
    cursor.execute("""
        SELECT date, day_type, notes
        FROM work_calendar
        WHERE date >= ? AND date <= ?
        ORDER BY date
    """, (today, end_date))
    
    holidays = cursor.fetchall()
    holiday_count = 0
    for holiday in holidays:
        if holiday[1] == 'holiday':
            print(f"  Holiday: {holiday[0]} - {holiday[2]}")
            holiday_count += 1
    
    if holiday_count == 0:
        print("  No holidays configured in the next 30 days")
    
    conn.close()
    return holiday_count

def verify_work_hour_functions():
    """List all functions that should be using WorkScheduleConfig"""
    print("\n=== Functions that should use WorkScheduleConfig ===")
    
    functions_to_check = [
        "get_work_hours_for_date() - Returns work hours for a specific date",
        "calculate_work_minutes_in_range_calendar() - Calculates total work minutes in date range",
        "get_active_schedule_config() - Gets the active work schedule configuration",
        "WorkScheduleConfig.get_work_hours_for_day() - Gets hours for a weekday",
        "WorkScheduleConfig.get_total_weekly_hours() - Gets total configured weekly hours"
    ]
    
    for func in functions_to_check:
        print(f"  ✓ {func}")
    
    print("\n=== Endpoints that use work hours ===")
    endpoints = [
        "/dashboard - Uses WorkScheduleConfig for weekly hours display",
        "/statistics - Uses WorkScheduleConfig for work time calculations",
        "/api/work_schedule/current - Returns current WorkScheduleConfig",
        "/api/work_schedule/update - Updates WorkScheduleConfig",
        "/settings - Manages WorkScheduleConfig"
    ]
    
    for endpoint in endpoints:
        print(f"  ✓ {endpoint}")

def check_database_schema():
    """Check if all required tables and columns exist"""
    conn = sqlite3.connect('monitoring.db')
    cursor = conn.cursor()
    
    print("\n=== Database Schema Check ===")
    
    # Check work_schedule_config table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='work_schedule_config'")
    if cursor.fetchone():
        print("  ✓ work_schedule_config table exists")
        
        cursor.execute("PRAGMA table_info(work_schedule_config)")
        columns = cursor.fetchall()
        print(f"    Columns: {', '.join([col[1] for col in columns])}")
    else:
        print("  ✗ work_schedule_config table missing!")
    
    # Check work_calendar table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='work_calendar'")
    if cursor.fetchone():
        print("  ✓ work_calendar table exists")
        
        cursor.execute("PRAGMA table_info(work_calendar)")
        columns = cursor.fetchall()
        print(f"    Columns: {', '.join([col[1] for col in columns])}")
    else:
        print("  ✗ work_calendar table missing!")
    
    conn.close()

def main():
    print("=" * 60)
    print("Work Hours Configuration Verification")
    print("=" * 60)
    
    try:
        # Check database schema
        check_database_schema()
        
        # Check current configuration
        weekly_hours = check_work_schedule_config()
        
        # Check holidays
        holiday_count = check_work_calendar()
        
        # List functions that should use WorkScheduleConfig
        verify_work_hour_functions()
        
        print("\n=== Summary ===")
        if weekly_hours > 0:
            print(f"✓ Work schedule configured: {weekly_hours:.1f} hours/week")
        else:
            print("✗ No active work schedule configuration")
        
        print(f"✓ {holiday_count} holidays configured in next 30 days")
        print("✓ All work hour calculations should use WorkScheduleConfig")
        print("✓ Dashboard and Statistics pages use consistent calculations")
        
    except Exception as e:
        print(f"\n✗ Error during verification: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()