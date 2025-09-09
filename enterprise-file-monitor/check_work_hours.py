#!/usr/bin/env python3
"""
Check and update work hours configuration
"""

from app import app, db, WorkScheduleConfig

def check_work_hours():
    with app.app_context():
        # Get the active schedule
        schedule = WorkScheduleConfig.query.filter_by(is_active=True).first()
        
        if not schedule:
            print("No active work schedule found. Creating default...")
            schedule = WorkScheduleConfig(is_active=True)
            db.session.add(schedule)
            db.session.commit()
        
        print("\nCurrent Work Schedule Configuration:")
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
                work_hours = schedule.get_work_hours_for_day(days.index(day))
                print(f"{day:10}: {start_hr:02d}:{start_min:02d} - {end_hr:02d}:{end_min:02d} ({work_hours:.1f} hours)")
        
        print(f"\nBreak: {schedule.break_start:.1f} for {schedule.break_duration:.1f} hours")
        
        # Ask if user wants to update
        print("\n" + "=" * 50)
        update = input("\nDo you want to update the work hours? (y/n): ").lower()
        
        if update == 'y':
            print("\nEnter new work hours (format: HH:MM or press Enter to keep current)")
            print("Enter 'off' to mark as non-working day\n")
            
            for day, attr in zip(days, day_attrs):
                current_start = getattr(schedule, f"{attr}_start")
                current_end = getattr(schedule, f"{attr}_end")
                
                if current_start == 0.0 and current_end == 0.0:
                    current = "OFF"
                else:
                    start_hr = int(current_start)
                    start_min = int((current_start - start_hr) * 60)
                    end_hr = int(current_end)
                    end_min = int((current_end - end_hr) * 60)
                    current = f"{start_hr:02d}:{start_min:02d} - {end_hr:02d}:{end_min:02d}"
                
                print(f"\n{day} (current: {current})")
                
                start_input = input(f"  Start time: ").strip()
                if start_input.lower() == 'off':
                    setattr(schedule, f"{attr}_start", 0.0)
                    setattr(schedule, f"{attr}_end", 0.0)
                    continue
                elif start_input:
                    try:
                        h, m = map(int, start_input.split(':'))
                        setattr(schedule, f"{attr}_start", h + m/60.0)
                    except:
                        print("  Invalid format, keeping current")
                
                end_input = input(f"  End time: ").strip()
                if end_input:
                    try:
                        h, m = map(int, end_input.split(':'))
                        setattr(schedule, f"{attr}_end", h + m/60.0)
                    except:
                        print("  Invalid format, keeping current")
            
            # Update break
            print(f"\nBreak (current: {schedule.break_start:.1f} for {schedule.break_duration:.1f} hours)")
            break_start = input("Break start time (HH:MM): ").strip()
            if break_start:
                try:
                    h, m = map(int, break_start.split(':'))
                    schedule.break_start = h + m/60.0
                except:
                    print("Invalid format, keeping current")
            
            break_dur = input("Break duration (hours, e.g., 0.5 for 30 min): ").strip()
            if break_dur:
                try:
                    schedule.break_duration = float(break_dur)
                except:
                    print("Invalid format, keeping current")
            
            db.session.commit()
            print("\n✅ Work schedule updated successfully!")
            
            # Show updated schedule
            print("\nUpdated Schedule:")
            print("=" * 50)
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
                    work_hours = schedule.get_work_hours_for_day(days.index(day))
                    print(f"{day:10}: {start_hr:02d}:{start_min:02d} - {end_hr:02d}:{end_min:02d} ({work_hours:.1f} hours)")

if __name__ == '__main__':
    check_work_hours()