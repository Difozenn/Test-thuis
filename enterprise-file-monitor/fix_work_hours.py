#!/usr/bin/env python3
"""
Fix work hours to the correct defaults:
Mon-Thu: 7:30-16:00 (8 hours with 30 min break = 8.0 work hours)
Friday: 7:30-15:00 (7 hours with 30 min break = 7.0 work hours) 
Break: 12:00-12:30 (0.5 hours)
"""

from app import app, db, WorkScheduleConfig

def fix_work_hours():
    with app.app_context():
        # Get the active schedule
        schedule = WorkScheduleConfig.query.filter_by(is_active=True).first()
        
        if not schedule:
            print("No active work schedule found. Creating new one with correct defaults...")
            schedule = WorkScheduleConfig(
                is_active=True,
                monday_start=7.5,     # 7:30
                monday_end=16.0,      # 16:00
                tuesday_start=7.5,    # 7:30
                tuesday_end=16.0,     # 16:00
                wednesday_start=7.5,  # 7:30
                wednesday_end=16.0,   # 16:00
                thursday_start=7.5,   # 7:30
                thursday_end=16.0,    # 16:00
                friday_start=7.5,     # 7:30
                friday_end=15.0,      # 15:00
                saturday_start=0.0,   # OFF
                saturday_end=0.0,
                sunday_start=0.0,     # OFF
                sunday_end=0.0,
                break_start=12.0,     # 12:00
                break_duration=0.5    # 30 minutes
            )
            db.session.add(schedule)
        else:
            print("Updating existing work schedule to correct values...")
            # Monday-Thursday: 7:30-16:00
            schedule.monday_start = 7.5
            schedule.monday_end = 16.0
            schedule.tuesday_start = 7.5
            schedule.tuesday_end = 16.0
            schedule.wednesday_start = 7.5
            schedule.wednesday_end = 16.0
            schedule.thursday_start = 7.5
            schedule.thursday_end = 16.0
            
            # Friday: 7:30-15:00
            schedule.friday_start = 7.5
            schedule.friday_end = 15.0
            
            # Weekend: OFF
            schedule.saturday_start = 0.0
            schedule.saturday_end = 0.0
            schedule.sunday_start = 0.0
            schedule.sunday_end = 0.0
            
            # Break: 12:00-12:30
            schedule.break_start = 12.0
            schedule.break_duration = 0.5
        
        db.session.commit()
        print("✅ Work schedule updated successfully!")
        
        # Display the updated schedule
        print("\nUpdated Work Schedule:")
        print("=" * 50)
        
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_attrs = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        
        for day, attr in zip(days, day_attrs):
            start = getattr(schedule, f"{attr}_start")
            end = getattr(schedule, f"{attr}_end")
            
            if start == 0.0 and end == 0.0:
                print(f"{day:10}: OFF")
            else:
                start_hr = int(start)
                start_min = int((start - start_hr) * 60)
                end_hr = int(end)
                end_min = int((end - end_hr) * 60)
                
                # Calculate work hours (total - break)
                total_hours = end - start
                work_hours = total_hours - schedule.break_duration if start < schedule.break_start < end else total_hours
                
                print(f"{day:10}: {start_hr:02d}:{start_min:02d} - {end_hr:02d}:{end_min:02d} ({work_hours:.1f} work hours)")
        
        print(f"\nBreak: 12:00-12:30 (30 minutes)")
        print(f"Weekly work hours: {40.0} hours (Mon-Thu: 8.0 × 4 = 32.0, Fri: 7.0)")

if __name__ == '__main__':
    fix_work_hours()