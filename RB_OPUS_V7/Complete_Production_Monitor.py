#!/usr/bin/env python3
"""
Complete Production Monitor
Integrates TwinCAT monitoring, cycle time calculation, and serial work tracking
with separate output files for each component
"""

import os
import json
import time
import threading
from datetime import datetime
from pathlib import Path

# Import our components
try:
    from TwinCAT_Auto_Monitor import TwinCATAutoMonitor
    TWINCAT_AVAILABLE = True
except ImportError:
    TWINCAT_AVAILABLE = False

try:
    from CycleTimeCalculator import CycleTimeCalculator
    CYCLE_CALC_AVAILABLE = True
except ImportError:
    CYCLE_CALC_AVAILABLE = False

try:
    from SerialWorkTracker import SerialWorkTracker
    SERIAL_TRACKER_AVAILABLE = True
except ImportError:
    SERIAL_TRACKER_AVAILABLE = False

class ProductionMonitorOutputs:
    """Manages all output files for the production monitor"""
    
    def __init__(self, base_dir="."):
        self.base_dir = Path(base_dir)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Output file paths
        self.twincat_log = self.base_dir / f"twincat_activity_{self.timestamp}.log"
        self.cycle_reports_dir = self.base_dir / "cycle_reports"
        self.production_data = self.base_dir / "production_data.json"
        self.summary_report = self.base_dir / f"production_summary_{self.timestamp}.txt"
        self.realtime_log = self.base_dir / "realtime_activity.log"
        
        # Create directories
        self.cycle_reports_dir.mkdir(exist_ok=True)
        
        # Initialize files
        self.init_output_files()
        
    def init_output_files(self):
        """Initialize output files with headers"""
        # TwinCAT activity log
        with open(self.twincat_log, 'w') as f:
            f.write(f"TwinCAT Activity Log - Started: {datetime.now()}\n")
            f.write("=" * 60 + "\n")
            f.write("Format: [TIMESTAMP] SOURCE: ACTIVITY\n\n")
            
        # Real-time activity log
        with open(self.realtime_log, 'w') as f:
            f.write(f"Real-time Activity Monitor - Started: {datetime.now()}\n")
            f.write("=" * 60 + "\n\n")
            
        print(f"📁 Output files initialized:")
        print(f"   TwinCAT Log: {self.twincat_log}")
        print(f"   Cycle Reports: {self.cycle_reports_dir}")
        print(f"   Production Data: {self.production_data}")
        print(f"   Summary Report: {self.summary_report}")
        print(f"   Real-time Log: {self.realtime_log}")
        
    def log_twincat_activity(self, source, activity):
        """Log TwinCAT activity to dedicated file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        log_entry = f"[{timestamp}] {source}: {activity}\n"
        
        with open(self.twincat_log, 'a') as f:
            f.write(log_entry)
            
        # Also log to real-time file (last 100 entries)
        self._append_realtime_log(f"TwinCAT - {source}: {activity}")
        
    def log_execution_detected(self, program_name, detection_method):
        """Log when execution is detected"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] EXECUTION DETECTED: {program_name} via {detection_method}\n"
        
        with open(self.twincat_log, 'a') as f:
            f.write(log_entry)
            
        self._append_realtime_log(f"🚀 EXECUTION: {program_name} ({detection_method})")
        
    def save_cycle_report(self, program_name, report_content):
        """Save cycle time report for a program"""
        report_file = self.cycle_reports_dir / f"{program_name}_cycle_report.txt"
        
        with open(report_file, 'w') as f:
            f.write(report_content)
            
        print(f"📊 Cycle report saved: {report_file}")
        
    def update_production_data(self, data):
        """Update production data JSON file"""
        with open(self.production_data, 'w') as f:
            json.dump(data, f, indent=2, default=str)
            
    def generate_summary_report(self, stats):
        """Generate comprehensive summary report"""
        lines = [
            f"Complete Production Monitor Summary",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"=== DETECTION STATISTICS ===",
            f"TwinCAT Activities Detected: {stats.get('twincat_activities', 0)}",
            f"Program Executions Detected: {stats.get('executions_detected', 0)}",
            f"Cycle Time Calculations: {stats.get('cycle_calculations', 0)}",
            f"",
            f"=== DETECTION METHODS ===",
            f"ADS Detection: {'✅ Active' if stats.get('ads_active') else '❌ Inactive'}",
            f"Process Monitoring: {'✅ Active' if stats.get('process_active') else '❌ Inactive'}",
            f"File Monitoring: {'✅ Active' if stats.get('file_active') else '❌ Inactive'}",
            f"",
            f"=== OUTPUT FILES ===",
            f"TwinCAT Log: {self.twincat_log.name}",
            f"Cycle Reports: {self.cycle_reports_dir.name}/",
            f"Production Data: {self.production_data.name}",
            f"Real-time Log: {self.realtime_log.name}",
        ]
        
        if stats.get('programs_analyzed'):
            lines.extend([
                f"",
                f"=== PROGRAMS ANALYZED ===",
            ])
            for program, data in stats['programs_analyzed'].items():
                lines.append(f"{program}:")
                lines.append(f"  Estimated Cycle Time: {data.get('cycle_time', 0)/60:.1f} min")
                lines.append(f"  Executions Detected: {data.get('executions', 0)}")
                
        report_content = '\n'.join(lines)
        
        with open(self.summary_report, 'w') as f:
            f.write(report_content)
            
        return report_content
        
    def _append_realtime_log(self, message):
        """Append to real-time log (keep last 100 entries)"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}\n"
        
        # Read existing lines
        try:
            with open(self.realtime_log, 'r') as f:
                lines = f.readlines()
        except FileNotFoundError:
            lines = []
            
        # Keep header + last 100 entries
        header_lines = 3  # Keep first 3 lines (header)
        if len(lines) > header_lines:
            content_lines = lines[header_lines:]
            if len(content_lines) >= 100:
                lines = lines[:header_lines] + content_lines[-99:] + [log_entry]
            else:
                lines.append(log_entry)
        else:
            lines.append(log_entry)
            
        # Write back
        with open(self.realtime_log, 'w') as f:
            f.writelines(lines)

class CompleteProductionMonitor:
    """Integrated production monitoring system"""
    
    def __init__(self, watch_directory="."):
        self.watch_directory = Path(watch_directory)
        self.outputs = ProductionMonitorOutputs(watch_directory)
        self.running = False
        
        # Component tracking
        self.stats = {
            'twincat_activities': 0,
            'executions_detected': 0,
            'cycle_calculations': 0,
            'ads_active': False,
            'process_active': False,
            'file_active': False,
            'programs_analyzed': {}
        }
        
        # Initialize components
        self.twincat_monitor = None
        self.cycle_calculator = None
        self.serial_tracker = None
        
    def initialize_components(self):
        """Initialize all monitoring components"""
        print("🚀 Complete Production Monitor - Initializing Components")
        print("=" * 60)
        
        # Initialize TwinCAT monitoring
        if TWINCAT_AVAILABLE:
            print("📡 Initializing TwinCAT monitoring...")
            self.twincat_monitor = TwinCATAutoMonitor()
            if self.twincat_monitor.auto_discover_and_setup():
                print("✅ TwinCAT monitoring ready")
                # Override the logging method to use our outputs
                original_log = self.twincat_monitor._log_execution_event
                def custom_log(source, details):
                    self.outputs.log_twincat_activity(source, details)
                    self.stats['twincat_activities'] += 1
                    self.on_twincat_activity(source, details)
                self.twincat_monitor._log_execution_event = custom_log
            else:
                print("⚠️  TwinCAT monitoring setup failed")
        else:
            print("❌ TwinCAT monitoring not available")
            
        # Initialize cycle calculator
        if CYCLE_CALC_AVAILABLE:
            print("📊 Cycle time calculator ready")
            self.stats['cycle_calculations'] = 0
        else:
            print("❌ Cycle time calculator not available")
            
        # Initialize serial work tracker
        if SERIAL_TRACKER_AVAILABLE:
            print("📈 Serial work tracker ready")
            self.serial_tracker = SerialWorkTracker(str(self.watch_directory))
        else:
            print("❌ Serial work tracker not available")
            
        return True
        
    def start_monitoring(self):
        """Start complete monitoring system"""
        if not self.initialize_components():
            return False
            
        print("\n🎯 Starting Complete Production Monitoring")
        print("=" * 50)
        
        self.running = True
        
        # Start TwinCAT monitoring
        if self.twincat_monitor:
            self.twincat_monitor.start_monitoring()
            
        # Start NC file monitoring
        self._start_nc_file_monitoring()
        
        # Start periodic reporting
        self._start_periodic_reporting()
        
        print("✅ Complete monitoring system active!")
        print("📁 Check output files for results:")
        print(f"   Real-time: {self.outputs.realtime_log}")
        print(f"   TwinCAT: {self.outputs.twincat_log}")
        print(f"   Reports: {self.outputs.cycle_reports_dir}")
        
        return True
        
    def _start_nc_file_monitoring(self):
        """Monitor NC files in the directory"""
        def nc_monitor():
            known_files = set()
            last_check = {}
            
            while self.running:
                try:
                    # Find NC files
                    nc_files = list(self.watch_directory.glob("*.nc"))
                    
                    for nc_file in nc_files:
                        # Check for new files
                        if nc_file not in known_files:
                            known_files.add(nc_file)
                            self.on_nc_file_found(nc_file)
                            
                        # Check for modifications
                        try:
                            current_mtime = nc_file.stat().st_mtime
                            last_mtime = last_check.get(nc_file, 0)
                            
                            if current_mtime > last_mtime:
                                if time.time() - current_mtime > 5:  # File is stable
                                    self.on_nc_file_modified(nc_file)
                                last_check[nc_file] = current_mtime
                                
                        except Exception as e:
                            print(f"Error checking {nc_file}: {e}")
                            
                except Exception as e:
                    print(f"NC monitoring error: {e}")
                    
                time.sleep(2)  # Check every 2 seconds
                
        thread = threading.Thread(target=nc_monitor, daemon=True)
        thread.start()
        
    def _start_periodic_reporting(self):
        """Generate periodic summary reports"""
        def reporter():
            while self.running:
                time.sleep(60)  # Every minute
                self.generate_periodic_summary()
                
        thread = threading.Thread(target=reporter, daemon=True)
        thread.start()
        
    def on_twincat_activity(self, source, details):
        """Handle TwinCAT activity detection"""
        # Check if this indicates program execution
        execution_indicators = ['running', 'high activity', 'modified', 'cycle']
        
        if any(indicator in details.lower() for indicator in execution_indicators):
            self.on_execution_detected("Unknown_Program", source)
            
    def on_nc_file_found(self, nc_file):
        """Handle new NC file discovery"""
        print(f"📝 New NC file found: {nc_file.name}")
        self.analyze_nc_file(nc_file)
        
    def on_nc_file_modified(self, nc_file):
        """Handle NC file modification (potential execution)"""
        print(f"🔄 NC file modified: {nc_file.name}")
        self.on_execution_detected(nc_file.name, "File_Modification")
        
    def on_execution_detected(self, program_name, detection_method):
        """Handle execution detection from any source"""
        self.stats['executions_detected'] += 1
        self.outputs.log_execution_detected(program_name, detection_method)
        
        # Record in serial tracker if available
        if self.serial_tracker and program_name.endswith('.nc'):
            self.serial_tracker.record_execution(program_name)
            
        print(f"🚀 EXECUTION DETECTED: {program_name} via {detection_method}")
        
    def analyze_nc_file(self, nc_file):
        """Analyze NC file for cycle time"""
        if not CYCLE_CALC_AVAILABLE:
            return
            
        try:
            calculator = CycleTimeCalculator(str(nc_file))
            calculator.load_machine_config_from_ini()
            calculator.parse_nc_file()
            results = calculator.calculate_cycle_time()
            
            # Generate report
            report = calculator.generate_report()
            self.outputs.save_cycle_report(nc_file.stem, report)
            
            # Update stats
            self.stats['cycle_calculations'] += 1
            self.stats['programs_analyzed'][nc_file.name] = {
                'cycle_time': results['total_time'],
                'executions': 0
            }
            
            print(f"📊 Cycle analysis complete: {nc_file.name} = {results['total_time']/60:.1f} min")
            
        except Exception as e:
            print(f"Error analyzing {nc_file}: {e}")
            
    def generate_periodic_summary(self):
        """Generate periodic summary"""
        report = self.outputs.generate_summary_report(self.stats)
        
        # Update production data
        if self.serial_tracker:
            production_data = {
                'timestamp': datetime.now().isoformat(),
                'stats': self.stats,
                'programs': getattr(self.serial_tracker, 'programs', {})
            }
            self.outputs.update_production_data(production_data)
            
    def stop_monitoring(self):
        """Stop all monitoring"""
        self.running = False
        
        if self.twincat_monitor:
            self.twincat_monitor.stop_monitoring()
            
        # Generate final report
        print("\n📋 Generating final summary...")
        final_report = self.outputs.generate_summary_report(self.stats)
        print(f"✅ Final report saved: {self.outputs.summary_report}")
        
        print("🛑 Complete production monitoring stopped")
        
    def show_testing_guide(self):
        """Show testing instructions"""
        print("\n🧪 TESTING GUIDE")
        print("=" * 40)
        print("How to test this system:")
        print()
        print("1. 📁 File Detection Test:")
        print("   - Copy Field1.nc to this directory")
        print("   - Modify Field1.nc (open in notepad, add a comment)")
        print("   - Should detect: File found + File modified")
        print()
        print("2. 🖥️ TwinCAT Test:")
        print("   - Start TwinCAT XAE")
        print("   - Create a simple project")
        print("   - Build and run the project")
        print("   - Should detect: Process activity + ADS state changes")
        print()
        print("3. 📊 Results Check:")
        print(f"   - Real-time activity: {self.outputs.realtime_log}")
        print(f"   - TwinCAT log: {self.outputs.twincat_log}")
        print(f"   - Cycle reports: {self.outputs.cycle_reports_dir}")
        print()
        print("🎯 Success Indicators:")
        print("   - Process monitoring: 90% chance (if TwinCAT installed)")
        print("   - File monitoring: 95% chance (almost guaranteed)")
        print("   - ADS monitoring: 60% chance (depends on TwinCAT runtime)")
        print("   - Real execution detection: 30-70% (depends on setup)")

def main():
    import sys
    
    print("Complete Production Monitor")
    print("Integrates TwinCAT monitoring + Cycle calculation + Serial tracking")
    print()
    
    # Get directory to monitor
    if len(sys.argv) > 1:
        watch_dir = sys.argv[1]
    else:
        watch_dir = "."
        
    monitor = CompleteProductionMonitor(watch_dir)
    
    # Show testing guide
    monitor.show_testing_guide()
    
    print("\nStarting monitoring...")
    
    if monitor.start_monitoring():
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping...")
            monitor.stop_monitoring()
    else:
        print("❌ Failed to start monitoring")

if __name__ == "__main__":
    main()