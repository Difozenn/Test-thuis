#!/usr/bin/env python3
"""
Import historical Accura SystemLog backup files into the database
This script reads backup files and creates events with proper timestamps
"""

import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
import argparse

# Add the app directory to path to import the models
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Event, CNCAnalysis, User, MonitoredPath

def parse_accura_log_file(filepath):
    """Parse an Accura SystemLog file and extract entries with timestamps"""
    entries = []
    current_date = None
    
    # Try to extract date from filename (e.g., SystemLog_20250108.txt)
    filename = os.path.basename(filepath)
    date_match = re.match(r'SystemLog_(\d{8})\.txt', filename)
    if date_match:
        date_str = date_match.group(1)
        current_date = datetime.strptime(date_str, '%Y%m%d').date()
        print(f"Extracted date from filename: {current_date}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                # Check for date line (DD.MM.YYYY)
                date_match = re.match(r'^(\d{2})\.(\d{2})\.(\d{4})$', line)
                if date_match:
                    day = int(date_match.group(1))
                    month = int(date_match.group(2))
                    year = int(date_match.group(3))
                    current_date = datetime(year, month, day).date()
                    print(f"Found date in file: {current_date}")
                    continue
                
                # Parse entry lines (HH:mm:ss  Entry text  [data])
                time_match = re.match(r'^(\d{2}):(\d{2}):(\d{2})\s+(.+)', line)
                if not time_match:
                    continue
                
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
                second = int(time_match.group(3))
                entry_text = time_match.group(4)
                
                # Skip if we don't have a date yet
                if not current_date:
                    continue
                
                # Create full timestamp
                timestamp = datetime.combine(current_date, datetime.min.time())
                timestamp = timestamp.replace(hour=hour, minute=minute, second=second)
                
                # Check for our target patterns
                if 'M1 von KAM1 Retour1' in entry_text:
                    bc_match = re.search(r'M1 von KAM1 Retour1 BC=\s*(\d+)', entry_text)
                    if bc_match:
                        entry_name = f"M1 von KAM1 Retour1 BC={bc_match.group(1)}"
                        entries.append({
                            'timestamp': timestamp,
                            'entry': entry_name,
                            'type': 'production'
                        })
                
                elif 'Rifo 2 Ende erreicht' in entry_text:
                    entries.append({
                        'timestamp': timestamp,
                        'entry': 'Rifo 2 Ende erreicht',
                        'type': 'completion'
                    })
    
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")
    
    return entries

def import_entries_to_database(entries, user_id, path_id, machine_time_minutes=5.0):
    """Import parsed entries into the database"""
    
    with app.app_context():
        imported_count = 0
        skipped_count = 0
        
        for entry_data in entries:
            timestamp = entry_data['timestamp']
            entry_name = entry_data['entry']
            
            # Check if an event already exists for this timestamp and entry
            # This prevents duplicate imports
            existing = Event.query.filter_by(
                user_id=user_id,
                timestamp=timestamp,
                file_path=f"accura/SystemLog.txt"
            ).first()
            
            if existing:
                # Check if it has the same entry name in CNC analysis
                if existing.cnc_analysis:
                    analysis = CNCAnalysis.query.filter_by(event_id=existing.id).first()
                    if analysis and analysis.file_path == entry_name:
                        skipped_count += 1
                        continue
            
            # Create new event
            event = Event(
                timestamp=timestamp,
                file_path="accura/SystemLog.txt",
                category_id=None,  # Will be determined by server
                matched_keyword=f"Accura Import: {entry_data['type']}",
                computer_name="ACCURA_IMPORT",
                user_id=user_id,
                event_type="imported",
                file_size=0
            )
            db.session.add(event)
            db.session.flush()  # Get the event ID
            
            # Create CNC analysis entry (using CNCAnalysis table for machine time tracking)
            cycle_time_seconds = machine_time_minutes * 60
            cnc_analysis = CNCAnalysis(
                event_id=event.id,
                file_path=entry_name,  # Store the entry name
                cycle_time_seconds=cycle_time_seconds,
                machine_time_minutes=machine_time_minutes,
                tool_changes=0,
                rapid_moves=0,
                feed_moves=0,
                spindle_commands=0
            )
            db.session.add(cnc_analysis)
            imported_count += 1
            
            # Commit every 100 entries to avoid memory issues
            if imported_count % 100 == 0:
                db.session.commit()
                print(f"  Imported {imported_count} entries so far...")
        
        # Final commit
        db.session.commit()
        
        return imported_count, skipped_count

def main():
    parser = argparse.ArgumentParser(description='Import Accura SystemLog backup files')
    parser.add_argument('path', help='Path to Accura backup directory or specific log file')
    parser.add_argument('--user', required=True, help='Username for the imported data')
    parser.add_argument('--machine-time', type=float, default=5.0, 
                       help='Machine time in minutes per entry (default: 5.0)')
    parser.add_argument('--pattern', default='SystemLog*.txt',
                       help='File pattern to match (default: SystemLog*.txt)')
    
    args = parser.parse_args()
    
    # Get the user
    with app.app_context():
        user = User.query.filter_by(username=args.user).first()
        if not user:
            print(f"Error: User '{args.user}' not found")
            sys.exit(1)
        
        # Get or create monitored path for Accura
        accura_path = MonitoredPath.query.filter_by(
            user_id=user.id,
            path='accura'
        ).first()
        
        if not accura_path:
            # Create the monitored path
            accura_path = MonitoredPath(
                path='accura',
                user_id=user.id,
                is_active=True,
                is_directory=True,
                recursive=False,
                description='Accura SystemLog monitoring'
            )
            db.session.add(accura_path)
            db.session.commit()
            print(f"Created monitored path for 'accura' directory")
        
        path_id = accura_path.id
    
    # Find files to import
    path = Path(args.path)
    if path.is_file():
        files_to_import = [path]
    elif path.is_dir():
        files_to_import = sorted(path.glob(args.pattern))
    else:
        print(f"Error: {args.path} is not a valid file or directory")
        sys.exit(1)
    
    if not files_to_import:
        print(f"No files found matching pattern '{args.pattern}' in {args.path}")
        sys.exit(1)
    
    print(f"Found {len(files_to_import)} files to import")
    
    total_imported = 0
    total_skipped = 0
    
    for filepath in files_to_import:
        print(f"\nProcessing: {filepath}")
        
        # Parse the file
        entries = parse_accura_log_file(filepath)
        print(f"  Found {len(entries)} relevant entries")
        
        if entries:
            # Import to database
            imported, skipped = import_entries_to_database(
                entries, 
                user.id, 
                path_id,
                args.machine_time
            )
            
            print(f"  Imported: {imported}, Skipped (duplicates): {skipped}")
            total_imported += imported
            total_skipped += skipped
    
    print(f"\n{'='*50}")
    print(f"Import complete!")
    print(f"Total imported: {total_imported}")
    print(f"Total skipped (duplicates): {total_skipped}")
    print(f"Machine time used: {args.machine_time} minutes per entry")

if __name__ == '__main__':
    main()