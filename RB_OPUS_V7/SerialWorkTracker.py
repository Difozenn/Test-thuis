#!/usr/bin/env python3
"""
Serial Work Tracker for RB_OPUS_V7 CNC Programs
Monitors Field*.nc files and tracks execution cycles
Integrates with existing file monitoring systems
"""

import os
import json
import time
import hashlib
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
from CycleTimeCalculator import CycleTimeCalculator

@dataclass
class ExecutionRecord:
    """Record of a single program execution"""
    timestamp: str
    program_name: str
    estimated_cycle_time: float
    execution_count: int
    file_size: int
    file_hash: str

@dataclass
class ProgramStats:
    """Statistics for a specific program"""
    program_name: str
    total_executions: int
    estimated_cycle_time: float
    total_estimated_time: float
    first_execution: str
    last_execution: str
    file_size: int
    file_hash: str
    daily_counts: Dict[str, int]  # date -> count
    hourly_pattern: Dict[int, int]  # hour -> count

class SerialWorkTracker:
    """Tracks serial work execution and cycle times"""
    
    def __init__(self, watch_directory: str = None, data_file: str = "serial_work_data.json"):
        self.watch_directory = watch_directory or os.getcwd()
        self.data_file = os.path.join(self.watch_directory, data_file)
        self.programs: Dict[str, ProgramStats] = {}
        self.execution_log: List[ExecutionRecord] = []
        
        # Load existing data
        self.load_data()
        
        # Cache for cycle time calculations
        self.cycle_time_cache: Dict[str, float] = {}

    def get_file_hash(self, file_path: str) -> str:
        """Calculate MD5 hash of file to detect changes"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""

    def calculate_cycle_time(self, nc_file: str) -> float:
        """Calculate cycle time for NC program, with caching"""
        file_path = os.path.join(self.watch_directory, nc_file)
        
        if not os.path.exists(file_path):
            return 0.0
            
        # Check if we have cached result
        file_hash = self.get_file_hash(file_path)
        cache_key = f"{nc_file}_{file_hash}"
        
        if cache_key in self.cycle_time_cache:
            return self.cycle_time_cache[cache_key]
            
        # Calculate cycle time
        try:
            calculator = CycleTimeCalculator(file_path)
            calculator.load_machine_config_from_ini()
            calculator.parse_nc_file()
            results = calculator.calculate_cycle_time()
            
            cycle_time = results['total_time']
            self.cycle_time_cache[cache_key] = cycle_time
            return cycle_time
            
        except Exception as e:
            print(f"Error calculating cycle time for {nc_file}: {e}")
            return 0.0

    def detect_program_execution(self, nc_file: str) -> bool:
        """Detect if a program has been executed (file access/modification)"""
        file_path = os.path.join(self.watch_directory, nc_file)
        
        if not os.path.exists(file_path):
            return False
            
        # Check file modification time
        try:
            stat = os.stat(file_path)
            mtime = stat.st_mtime
            current_time = time.time()
            
            # If modified within last 5 minutes, consider it executed
            if current_time - mtime < 300:  # 5 minutes
                return True
                
        except Exception:
            pass
            
        return False

    def record_execution(self, nc_file: str, force: bool = False) -> None:
        """Record an execution of the NC program"""
        file_path = os.path.join(self.watch_directory, nc_file)
        
        if not os.path.exists(file_path) and not force:
            print(f"Warning: {nc_file} not found")
            return
            
        now = datetime.now()
        timestamp = now.isoformat()
        today = now.date().isoformat()
        hour = now.hour
        
        # Get file info
        try:
            file_size = os.path.getsize(file_path)
            file_hash = self.get_file_hash(file_path)
        except Exception:
            file_size = 0
            file_hash = ""
            
        # Calculate cycle time
        estimated_cycle_time = self.calculate_cycle_time(nc_file)
        
        # Update or create program stats
        if nc_file not in self.programs:
            self.programs[nc_file] = ProgramStats(
                program_name=nc_file,
                total_executions=0,
                estimated_cycle_time=estimated_cycle_time,
                total_estimated_time=0.0,
                first_execution=timestamp,
                last_execution=timestamp,
                file_size=file_size,
                file_hash=file_hash,
                daily_counts={},
                hourly_pattern={}
            )
        
        stats = self.programs[nc_file]
        stats.total_executions += 1
        stats.estimated_cycle_time = estimated_cycle_time
        stats.total_estimated_time += estimated_cycle_time
        stats.last_execution = timestamp
        stats.file_size = file_size
        stats.file_hash = file_hash
        
        # Update daily counts
        if today not in stats.daily_counts:
            stats.daily_counts[today] = 0
        stats.daily_counts[today] += 1
        
        # Update hourly pattern
        if hour not in stats.hourly_pattern:
            stats.hourly_pattern[hour] = 0
        stats.hourly_pattern[hour] += 1
        
        # Add to execution log
        execution_record = ExecutionRecord(
            timestamp=timestamp,
            program_name=nc_file,
            estimated_cycle_time=estimated_cycle_time,
            execution_count=stats.total_executions,
            file_size=file_size,
            file_hash=file_hash
        )
        
        self.execution_log.append(execution_record)
        
        # Keep only last 1000 execution records
        if len(self.execution_log) > 1000:
            self.execution_log = self.execution_log[-1000:]
            
        print(f"Recorded execution #{stats.total_executions} of {nc_file} (Est. {estimated_cycle_time/60:.1f} min)")

    def monitor_directory(self, check_interval: int = 30) -> None:
        """Monitor directory for NC file executions"""
        print(f"Monitoring directory: {self.watch_directory}")
        print(f"Check interval: {check_interval} seconds")
        print("Press Ctrl+C to stop monitoring")
        
        last_check = {}
        
        try:
            while True:
                # Find all NC files
                nc_files = []
                for file in os.listdir(self.watch_directory):
                    if file.lower().endswith('.nc'):
                        nc_files.append(file)
                
                # Check each NC file for execution
                for nc_file in nc_files:
                    file_path = os.path.join(self.watch_directory, nc_file)
                    
                    try:
                        current_mtime = os.path.getmtime(file_path)
                        last_mtime = last_check.get(nc_file, 0)
                        
                        # If file was modified since last check, record execution
                        if current_mtime > last_mtime:
                            # Only record if file is older than 5 seconds (avoid recording during write)
                            if time.time() - current_mtime > 5:
                                self.record_execution(nc_file)
                                self.save_data()
                                
                        last_check[nc_file] = current_mtime
                        
                    except Exception as e:
                        print(f"Error checking {nc_file}: {e}")
                
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            print("\nMonitoring stopped")
            self.save_data()

    def manual_record(self, nc_file: str, count: int = 1) -> None:
        """Manually record executions (for testing or catch-up)"""
        for i in range(count):
            self.record_execution(nc_file, force=True)
        self.save_data()

    def generate_summary_report(self) -> str:
        """Generate a summary report of all tracked programs"""
        if not self.programs:
            return "No programs tracked yet."
            
        lines = [
            f"Serial Work Tracking Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Tracking Directory: {self.watch_directory}",
            f"",
            f"=== PROGRAM SUMMARY ===",
        ]
        
        # Sort programs by total executions
        sorted_programs = sorted(
            self.programs.values(), 
            key=lambda p: p.total_executions, 
            reverse=True
        )
        
        total_executions = sum(p.total_executions for p in sorted_programs)
        total_estimated_time = sum(p.total_estimated_time for p in sorted_programs)
        
        for stats in sorted_programs:
            avg_time = stats.total_estimated_time / stats.total_executions if stats.total_executions > 0 else 0
            lines.extend([
                f"",
                f"Program: {stats.program_name}",
                f"  Total Executions: {stats.total_executions}",
                f"  Avg Cycle Time: {avg_time/60:.1f} min",
                f"  Total Est. Time: {stats.total_estimated_time/3600:.1f} hours",
                f"  First Run: {stats.first_execution[:19]}",
                f"  Last Run: {stats.last_execution[:19]}",
            ])
            
            # Today's count
            today = datetime.now().date().isoformat()
            today_count = stats.daily_counts.get(today, 0)
            if today_count > 0:
                lines.append(f"  Today's Count: {today_count}")
        
        lines.extend([
            f"",
            f"=== OVERALL STATISTICS ===",
            f"Total Programs: {len(self.programs)}",
            f"Total Executions: {total_executions}",
            f"Total Est. Production Time: {total_estimated_time/3600:.1f} hours",
            f"Recent Executions (last 10):",
        ])
        
        # Show recent executions
        recent = self.execution_log[-10:] if self.execution_log else []
        for record in reversed(recent):
            lines.append(f"  {record.timestamp[:19]} - {record.program_name} (#{record.execution_count})")
        
        return '\n'.join(lines)

    def save_data(self) -> None:
        """Save tracking data to JSON file"""
        try:
            data = {
                'programs': {k: asdict(v) for k, v in self.programs.items()},
                'execution_log': [asdict(r) for r in self.execution_log],
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving data: {e}")

    def load_data(self) -> None:
        """Load tracking data from JSON file"""
        if not os.path.exists(self.data_file):
            return
            
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
            
            # Load programs
            if 'programs' in data:
                for name, prog_data in data['programs'].items():
                    self.programs[name] = ProgramStats(**prog_data)
            
            # Load execution log
            if 'execution_log' in data:
                for record_data in data['execution_log']:
                    self.execution_log.append(ExecutionRecord(**record_data))
                    
            print(f"Loaded data for {len(self.programs)} programs, {len(self.execution_log)} execution records")
            
        except Exception as e:
            print(f"Error loading data: {e}")

    def export_csv(self, output_file: str) -> None:
        """Export execution data to CSV"""
        try:
            import csv
            
            with open(output_file, 'w', newline='') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow([
                    'Timestamp', 'Program', 'Execution#', 'Estimated_Cycle_Time_Sec', 
                    'Estimated_Cycle_Time_Min', 'File_Size', 'File_Hash'
                ])
                
                # Write execution records
                for record in self.execution_log:
                    writer.writerow([
                        record.timestamp,
                        record.program_name,
                        record.execution_count,
                        f"{record.estimated_cycle_time:.1f}",
                        f"{record.estimated_cycle_time/60:.2f}",
                        record.file_size,
                        record.file_hash
                    ])
                    
            print(f"Exported {len(self.execution_log)} records to {output_file}")
            
        except Exception as e:
            print(f"Error exporting CSV: {e}")

def main():
    """Main function for command line usage"""
    import sys
    
    if len(sys.argv) < 2:
        print("Serial Work Tracker for RB_OPUS_V7")
        print("")
        print("Usage:")
        print("  python SerialWorkTracker.py monitor [directory] [interval]")
        print("  python SerialWorkTracker.py record <program.nc> [count]")
        print("  python SerialWorkTracker.py report [output.txt]")
        print("  python SerialWorkTracker.py export <output.csv>")
        print("")
        print("Examples:")
        print("  python SerialWorkTracker.py monitor . 30")
        print("  python SerialWorkTracker.py record Field1.nc 5")
        print("  python SerialWorkTracker.py report production_report.txt")
        print("  python SerialWorkTracker.py export execution_data.csv")
        return
    
    command = sys.argv[1].lower()
    
    if command == "monitor":
        directory = sys.argv[2] if len(sys.argv) > 2 else "."
        interval = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        
        tracker = SerialWorkTracker(directory)
        tracker.monitor_directory(interval)
        
    elif command == "record":
        if len(sys.argv) < 3:
            print("Error: Please specify NC program name")
            return
            
        program = sys.argv[2]
        count = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        
        tracker = SerialWorkTracker()
        tracker.manual_record(program, count)
        print(f"Recorded {count} execution(s) of {program}")
        
    elif command == "report":
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        
        tracker = SerialWorkTracker()
        report = tracker.generate_summary_report()
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report)
            print(f"Report saved to {output_file}")
        else:
            print(report)
            
    elif command == "export":
        if len(sys.argv) < 3:
            print("Error: Please specify output CSV file")
            return
            
        output_file = sys.argv[2]
        tracker = SerialWorkTracker()
        tracker.export_csv(output_file)
        
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()