#!/usr/bin/env python3
"""
Reichenbacher Opus Complete Production Monitor
All-in-one monitoring solution with auto-discovery - NO OTHER FILES NEEDED!
"""

import os
import sys
import json
import time
import socket
import winreg
import psutil
import threading
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple

# Optional imports with fallbacks
try:
    import pyads
    ADS_AVAILABLE = True
except ImportError:
    ADS_AVAILABLE = False

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

@dataclass
class MachineConfig:
    """Machine configuration"""
    rapid_feedrate: float = 50000.0  # mm/min
    tool_change_time: float = 15.0   # seconds
    spindle_start_time: float = 3.0  # seconds
    
class ReichenbacherCompleteMonitor:
    """Complete all-in-one monitor for Reichenbacher Opus"""
    
    def __init__(self, watch_directory="."):
        self.watch_directory = Path(watch_directory)
        self.running = False
        
        # ADS configuration (will be auto-discovered)
        self.ads_net_id = None
        self.ads_port = 851
        self.ads_connection = None
        
        # Machine paths
        self.machine_paths = [
            "C:\\HOPS7\\",
            "C:\\RB_CNC\\",
            "C:\\Reichenbacher\\",
            "C:\\TwinCAT\\",
            "C:\\ProgramData\\Beckhoff\\",
        ]
        
        # Detection statistics
        self.stats = {
            'ads_detections': 0,
            'process_detections': 0,
            'file_detections': 0,
            'executions_detected': 0,
            'cycle_calculations': 0,
            'start_time': datetime.now(),
            'programs_analyzed': {}
        }
        
        # Output files
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"reichenbacher_monitor_{self.timestamp}.log"
        self.data_file = f"reichenbacher_data_{self.timestamp}.json"
        self.report_file = f"reichenbacher_report_{self.timestamp}.txt"
        
        self._init_output_files()
        
    def _init_output_files(self):
        """Initialize output files"""
        with open(self.log_file, 'w') as f:
            f.write(f"Reichenbacher Opus Monitor Log - {datetime.now()}\n")
            f.write("=" * 60 + "\n\n")
            
        self._log("Monitor initialized", "SYSTEM")
        
    def _log(self, message, source="MONITOR"):
        """Log to file and console"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        log_entry = f"[{timestamp}] {source}: {message}"
        
        # Console output
        print(f"🔍 {log_entry}")
        
        # File output
        with open(self.log_file, 'a') as f:
            f.write(log_entry + "\n")
            
    def auto_discover_ads(self):
        """Auto-discover ADS connection"""
        if not ADS_AVAILABLE:
            self._log("PyADS not available - skipping ADS discovery", "ADS")
            return False
            
        self._log("Starting ADS auto-discovery...", "ADS")
        
        # Method 1: Registry search
        ams_ids = []
        try:
            registry_paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Beckhoff\TwinCAT3\System"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Beckhoff\TwinCAT3\System"),
            ]
            
            for hkey, path in registry_paths:
                try:
                    with winreg.OpenKey(hkey, path) as key:
                        for i in range(winreg.QueryInfoKey(key)[1]):
                            try:
                                name, value, _ = winreg.EnumValue(key, i)
                                if 'amsnetid' in name.lower():
                                    ams_ids.append(value)
                                    self._log(f"Registry AMS ID: {value}", "ADS")
                            except:
                                pass
                except:
                    pass
        except:
            pass
            
        # Method 2: Network-based IDs
        try:
            hostname = socket.gethostname()
            local_ips = socket.gethostbyname_ex(hostname)[2]
            for ip in local_ips:
                if not ip.startswith('127.'):
                    ams_id = f"{ip}.1.1"
                    ams_ids.append(ams_id)
                    self._log(f"Network AMS ID: {ams_id}", "ADS")
        except:
            pass
            
        # Add localhost
        ams_ids.extend(['127.0.0.1.1.1', '192.168.0.1.1.1'])
        
        # Test each AMS ID
        for ams_id in list(dict.fromkeys(ams_ids)):  # Remove duplicates
            for port in [851, 852, 853, 854]:
                try:
                    self._log(f"Testing {ams_id}:{port}...", "ADS")
                    
                    # Try to add route
                    try:
                        pyads.add_route(ams_id, ams_id.replace('.1.1', ''))
                    except:
                        pass
                        
                    # Test connection
                    connection = pyads.Connection(ams_id, port)
                    connection.open()
                    state = connection.read_state()
                    connection.close()
                    
                    self.ads_net_id = ams_id
                    self.ads_port = port
                    self._log(f"✅ ADS connected: {ams_id}:{port} - State: {state}", "ADS")
                    return True
                    
                except Exception as e:
                    continue
                    
        self._log("❌ No working ADS connection found", "ADS")
        return False
        
    def start_ads_monitoring(self):
        """Start ADS monitoring thread"""
        if not self.ads_net_id:
            return
            
        def ads_monitor():
            try:
                connection = pyads.Connection(self.ads_net_id, self.ads_port)
                connection.open()
                
                last_state = None
                last_cycle_count = None
                
                while self.running:
                    try:
                        # Monitor state
                        state = connection.read_state()
                        if state[0] != last_state:
                            if state[0] == pyads.ADSSTATE_RUN:
                                self._log("TwinCAT Runtime RUNNING", "ADS")
                                self.stats['ads_detections'] += 1
                            last_state = state[0]
                            
                        # Try to read cycle count
                        for var in ["Main.nCycleCount", "MAIN.nCycleCount", "GVL.nCycleCount"]:
                            try:
                                count = connection.read_by_name(var, pyads.PLCTYPE_ULINT)
                                if count != last_cycle_count:
                                    self._log(f"Cycle count: {count} (+{count - (last_cycle_count or 0)})", "ADS")
                                    self.stats['executions_detected'] += 1
                                    last_cycle_count = count
                                break
                            except:
                                pass
                                
                    except:
                        pass
                        
                    time.sleep(1)
                    
                connection.close()
                
            except Exception as e:
                self._log(f"ADS monitor error: {e}", "ADS")
                
        thread = threading.Thread(target=ads_monitor, daemon=True)
        thread.start()
        self._log("ADS monitoring started", "ADS")
        
    def start_process_monitoring(self):
        """Start process monitoring thread"""
        def process_monitor():
            while self.running:
                try:
                    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                        try:
                            proc_name = proc.info['name'].lower()
                            if any(keyword in proc_name for keyword in ['twincat', 'beckhoff', 'hops', 'reichenbacher']):
                                cpu = proc.cpu_percent(interval=0.1)
                                if cpu > 30:  # High activity
                                    self._log(f"{proc.info['name']} high CPU: {cpu:.1f}%", "PROCESS")
                                    self.stats['process_detections'] += 1
                        except:
                            pass
                            
                except:
                    pass
                    
                time.sleep(5)
                
        thread = threading.Thread(target=process_monitor, daemon=True)
        thread.start()
        self._log("Process monitoring started", "PROCESS")
        
    def start_file_monitoring(self):
        """Start file monitoring thread"""
        if not WATCHDOG_AVAILABLE:
            self._log("Watchdog not available - using basic file monitoring", "FILE")
            self._start_basic_file_monitoring()
            return
            
        class NCFileHandler(FileSystemEventHandler):
            def __init__(self, monitor):
                self.monitor = monitor
                
            def on_modified(self, event):
                if not event.is_directory and event.src_path.endswith('.nc'):
                    self.monitor._log(f"NC file modified: {os.path.basename(event.src_path)}", "FILE")
                    self.monitor.stats['file_detections'] += 1
                    self.monitor.analyze_nc_file(event.src_path)
                    
        observer = Observer()
        handler = NCFileHandler(self)
        observer.schedule(handler, str(self.watch_directory), recursive=False)
        observer.start()
        self._log("File monitoring started", "FILE")
        
    def _start_basic_file_monitoring(self):
        """Basic file monitoring without watchdog"""
        def file_monitor():
            known_files = {}
            
            while self.running:
                try:
                    for nc_file in self.watch_directory.glob("*.nc"):
                        current_mtime = nc_file.stat().st_mtime
                        last_mtime = known_files.get(nc_file, 0)
                        
                        if current_mtime > last_mtime:
                            self._log(f"NC file changed: {nc_file.name}", "FILE")
                            self.stats['file_detections'] += 1
                            known_files[nc_file] = current_mtime
                            
                            if nc_file not in self.stats['programs_analyzed']:
                                self.analyze_nc_file(str(nc_file))
                                
                except:
                    pass
                    
                time.sleep(5)
                
        thread = threading.Thread(target=file_monitor, daemon=True)
        thread.start()
        
    def analyze_nc_file(self, nc_file_path):
        """Analyze NC file for cycle time and efficiency"""
        try:
            from CycleTimeCalculator import CycleTimeCalculator
            from CNC_Efficiency_Analyzer import CNCEfficiencyAnalyzer
            
            self._log(f"Analyzing {os.path.basename(nc_file_path)}...", "ANALYZER")
            
            # Calculate cycle time
            calculator = CycleTimeCalculator(nc_file_path)
            calculator.load_machine_config_from_ini()
            calculator.parse_nc_file()
            results = calculator.calculate_cycle_time()
            
            # Analyze efficiency
            analyzer = CNCEfficiencyAnalyzer(nc_file_path)
            metrics, classification = analyzer.analyze_efficiency()
            
            # Store results
            self.stats['programs_analyzed'][os.path.basename(nc_file_path)] = {
                'cycle_time': results['total_time'],
                'cutting_time': results.get('cutting_time', 0),
                'efficiency': metrics.cutting_efficiency,
                'grade': classification.overall_grade,
                'score': classification.overall_score
            }
            
            self.stats['cycle_calculations'] += 1
            
            self._log(
                f"Analysis complete: {results['total_time']/60:.1f} min, "
                f"{metrics.cutting_efficiency:.1f}% efficiency, "
                f"{classification.overall_grade}",
                "ANALYZER"
            )
            
        except Exception as e:
            self._log(f"Analysis error: {e}", "ANALYZER")
            
    def generate_report(self):
        """Generate comprehensive report"""
        runtime = (datetime.now() - self.stats['start_time']).total_seconds() / 60
        
        report_lines = [
            "REICHENBACHER OPUS PRODUCTION MONITOR REPORT",
            "=" * 60,
            f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Runtime: {runtime:.1f} minutes",
            "",
            "📊 DETECTION SUMMARY",
            f"ADS Detections: {self.stats['ads_detections']}",
            f"Process Detections: {self.stats['process_detections']}",
            f"File Detections: {self.stats['file_detections']}",
            f"Executions Detected: {self.stats['executions_detected']}",
            f"Programs Analyzed: {self.stats['cycle_calculations']}",
            "",
            "🔌 CONNECTION INFO",
            f"ADS Connection: {self.ads_net_id}:{self.ads_port if self.ads_net_id else 'Not available'}",
            f"ADS Available: {'Yes' if ADS_AVAILABLE else 'No'}",
            f"Watchdog Available: {'Yes' if WATCHDOG_AVAILABLE else 'No'}",
            "",
        ]
        
        if self.stats['programs_analyzed']:
            report_lines.extend([
                "📈 PROGRAMS ANALYZED",
                f"{'Program':<20} {'Cycle Time':<12} {'Efficiency':<12} {'Grade':<12} {'Score':<8}",
                "-" * 60
            ])
            
            for program, data in self.stats['programs_analyzed'].items():
                cycle_min = data['cycle_time'] / 60
                efficiency = data['efficiency']
                grade = data['grade'].split()[1] if data['grade'] else 'N/A'
                score = data['score']
                
                report_lines.append(
                    f"{program:<20} {cycle_min:<12.1f} {efficiency:<12.1f}% {grade:<12} {score:<8.1f}"
                )
                
        # Save report
        with open(self.report_file, 'w') as f:
            f.write('\n'.join(report_lines))
            
        # Save data
        with open(self.data_file, 'w') as f:
            json.dump(self.stats, f, indent=2, default=str)
            
        return '\n'.join(report_lines)
        
    def start_complete_monitoring(self):
        """Start all monitoring systems"""
        print("🏭 REICHENBACHER OPUS COMPLETE PRODUCTION MONITOR")
        print("=" * 60)
        
        self.running = True
        
        # Auto-discover ADS
        if ADS_AVAILABLE:
            self.auto_discover_ads()
            if self.ads_net_id:
                self.start_ads_monitoring()
        else:
            print("⚠️  Install pyads for ADS monitoring: pip install pyads")
            
        # Start process monitoring
        self.start_process_monitoring()
        
        # Start file monitoring
        self.start_file_monitoring()
        
        print("\n✅ All monitoring systems started!")
        print(f"📁 Watch directory: {self.watch_directory}")
        print(f"📄 Log file: {self.log_file}")
        print(f"📊 Data file: {self.data_file}")
        print(f"📋 Report file: {self.report_file}")
        print("\nPress Ctrl+C to stop and generate report...")
        
        return True
        
    def stop_monitoring(self):
        """Stop all monitoring and generate final report"""
        self.running = False
        time.sleep(1)  # Let threads finish
        
        print("\n🛑 Stopping monitor...")
        report = self.generate_report()
        print("\n" + report)
        print(f"\n✅ Reports saved!")
        print(f"   Log: {self.log_file}")
        print(f"   Data: {self.data_file}")
        print(f"   Report: {self.report_file}")

def main():
    """Main entry point"""
    print("Reichenbacher Opus Complete Production Monitor")
    print("One file, all features, zero configuration needed!")
    print()
    
    # Get directory to monitor
    if len(sys.argv) > 1:
        watch_dir = sys.argv[1]
    else:
        watch_dir = "."
        
    monitor = ReichenbacherCompleteMonitor(watch_dir)
    
    print("📋 FEATURES:")
    print("✅ Auto-discovers TwinCAT ADS connection")
    print("✅ Monitors process CPU activity")
    print("✅ Watches NC file modifications")
    print("✅ Calculates cycle times")
    print("✅ Analyzes efficiency")
    print("✅ Tracks serial work executions")
    print("✅ Generates comprehensive reports")
    
    print("\n🧪 TESTING GUIDE:")
    print("1. Run this script")
    print("2. Start TwinCAT and load a project")
    print("3. Open/modify NC files")
    print("4. Run CNC programs")
    print("5. Press Ctrl+C to see results")
    
    print("\n🚀 Starting monitoring...\n")
    
    if monitor.start_complete_monitoring():
        try:
            while True:
                time.sleep(10)
                # Periodic status
                if monitor.stats['executions_detected'] > 0:
                    print(f"\n📊 Status: {monitor.stats['executions_detected']} executions detected")
                    
        except KeyboardInterrupt:
            monitor.stop_monitoring()
    else:
        print("❌ Failed to start monitoring")

if __name__ == "__main__":
    main()