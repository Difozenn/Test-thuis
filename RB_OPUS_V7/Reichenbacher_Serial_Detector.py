#!/usr/bin/env python3
"""
Reichenbacher Opus Serial Work Detector
Specialized detection for Reichenbacher machines with Beckhoff TwinCAT
Includes network, event logs, CNC logs, database, and power monitoring
"""

import os
import sys
import time
import json
import socket
import struct
import threading
import winreg
import win32evtlog
import win32evtlogutil
import win32con
import psutil
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3

try:
    from scapy.all import sniff, IP, TCP
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    print("⚠️  Scapy not available. Install with: pip install scapy")

class ReichenbacherSerialDetector:
    def __init__(self):
        self.running = False
        self.detection_log = []
        self.machine_ip = None
        self.cnc_ports = [851, 48898, 801, 5432]  # Common Beckhoff/CNC ports
        self.ads_net_id = None
        self.ads_port = 851
        
        # Reichenbacher specific paths
        self.reichenbacher_paths = [
            "C:\\HOPS7\\",
            "C:\\RB_CNC\\",
            "C:\\Reichenbacher\\",
            "C:\\CNC\\Reichenbacher\\",
            "D:\\HOPS7\\",
            "D:\\RB_CNC\\",
        ]
        
        # TwinCAT/Beckhoff paths
        self.twincat_paths = [
            "C:\\TwinCAT\\",
            "C:\\ProgramData\\Beckhoff\\",
            "C:\\Users\\Public\\Documents\\Beckhoff\\",
        ]
        
        # Detection counters
        self.detections = {
            'network': 0,
            'event_log': 0,
            'cnc_logs': 0,
            'database': 0,
            'power': 0,
            'file_access': 0
        }
        
    def start_all_detection_methods(self):
        """Start all serial work detection methods"""
        print("🏭 Reichenbacher Opus Serial Work Detector")
        print("=" * 50)
        
        # Auto-discover ADS connection first
        self._auto_discover_ads()
        
        self.running = True
        detection_threads = []
        
        # 1. Network Traffic Monitoring (including ADS)
        if SCAPY_AVAILABLE:
            thread1 = threading.Thread(target=self._monitor_network_traffic, daemon=True)
            thread1.start()
            detection_threads.append(("Network", thread1))
            print("✅ Network traffic monitoring started")
        else:
            print("❌ Network monitoring unavailable (install scapy)")
            
        # 2. Windows Event Log Monitoring
        try:
            thread2 = threading.Thread(target=self._monitor_windows_events, daemon=True)
            thread2.start()
            detection_threads.append(("Events", thread2))
            print("✅ Windows event monitoring started")
        except Exception as e:
            print(f"❌ Event monitoring failed: {e}")
            
        # 3. CNC Software Log Parsing
        thread3 = threading.Thread(target=self._monitor_cnc_logs, daemon=True)
        thread3.start()
        detection_threads.append(("CNC Logs", thread3))
        print("✅ CNC log monitoring started")
        
        # 4. Database/Registry Monitoring
        thread4 = threading.Thread(target=self._monitor_databases_registry, daemon=True)
        thread4.start()
        detection_threads.append(("Database", thread4))
        print("✅ Database/registry monitoring started")
        
        # 5. Power/Current Monitoring (via process CPU patterns)
        thread5 = threading.Thread(target=self._monitor_power_patterns, daemon=True)
        thread5.start()
        detection_threads.append(("Power", thread5))
        print("✅ Power pattern monitoring started")
        
        print(f"\n🎯 {len(detection_threads)} detection methods active")
        return detection_threads
        
    def _auto_discover_ads(self):
        """Auto-discover ADS connection for Reichenbacher"""
        try:
            from TwinCAT_ADS_Enhanced import TwinCATADSEnhanced
            print("\n🔍 Auto-discovering ADS connection...")
            
            enhanced = TwinCATADSEnhanced()
            if enhanced.find_working_connection():
                self.ads_net_id = enhanced.ams_net_id
                self.ads_port = enhanced.port
                self.machine_ip = self.ads_net_id.split('.')[0:4]  # Extract IP portion
                self.machine_ip = '.'.join(self.machine_ip)
                print(f"✅ Found Reichenbacher at {self.ads_net_id}:{self.ads_port}")
                print(f"   Machine IP: {self.machine_ip}")
            else:
                print("⚠️  ADS auto-discovery failed, using network scan")
        except Exception as e:
            print(f"⚠️  ADS discovery not available: {e}")
        
    def _monitor_network_traffic(self):
        """Monitor network traffic for DNC/CNC communication"""
        def packet_handler(packet):
            if not self.running:
                return
                
            try:
                if packet.haslayer(IP) and packet.haslayer(TCP):
                    dst_ip = packet[IP].dst
                    src_ip = packet[IP].src
                    dst_port = packet[TCP].dport
                    src_port = packet[TCP].sport
                    
                    # Look for CNC/TwinCAT traffic
                    if dst_port in self.cnc_ports or src_port in self.cnc_ports:
                        if hasattr(packet[TCP], 'load') and packet[TCP].load:
                            payload = packet[TCP].load
                            
                            # Look for NC file transfers or program commands
                            if any(pattern in payload for pattern in [b'Field', b'.nc', b'START', b'RUN', b'CYCLE']):
                                self._log_detection('network', f"CNC traffic detected: {src_ip}:{src_port} -> {dst_ip}:{dst_port}")
                                
                            # Look for TwinCAT ADS traffic
                            if dst_port == 851 or src_port == 851:
                                self._log_detection('network', f"TwinCAT ADS traffic: {src_ip} <-> {dst_ip}")
                                
            except Exception as e:
                pass  # Ignore packet parsing errors
                
        try:
            # Sniff network traffic (requires admin privileges)
            sniff(prn=packet_handler, store=0, timeout=1)
        except Exception as e:
            print(f"Network monitoring error (try running as admin): {e}")
            
    def _monitor_windows_events(self):
        """Monitor Windows event logs for CNC/TwinCAT activity"""
        server = 'localhost'
        
        # Monitor System and Application logs
        log_types = ['System', 'Application']
        
        for log_type in log_types:
            try:
                hand = win32evtlog.OpenEventLog(server, log_type)
                
                while self.running:
                    events = win32evtlog.ReadEventLog(
                        hand,
                        win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ,
                        0
                    )
                    
                    for event in events:
                        if not self.running:
                            break
                            
                        # Check for Reichenbacher/TwinCAT/Beckhoff events
                        event_strings = str(event.StringInserts) if event.StringInserts else ""
                        source_name = event.SourceName if hasattr(event, 'SourceName') else ""
                        
                        keywords = ['reichenbacher', 'twincat', 'beckhoff', 'opus', 'cnc', 'field1', 'hops']
                        
                        if any(keyword in event_strings.lower() or keyword in source_name.lower() 
                               for keyword in keywords):
                            self._log_detection('event_log', 
                                              f"Event: {source_name} - {event_strings[:100]}")
                            
                    time.sleep(5)  # Check every 5 seconds
                    
            except Exception as e:
                print(f"Event log monitoring error for {log_type}: {e}")
                
    def _monitor_cnc_logs(self):
        """Monitor CNC software logs for execution records"""
        log_patterns = [
            # Reichenbacher HOPS logs
            "**/HOPS*/**/logs/**/*.log",
            "**/HOPS*/**/log/**/*.txt", 
            "**/RB_CNC/**/*.log",
            
            # TwinCAT logs
            "**/TwinCAT/**/Target/**/*.log",
            "**/TwinCAT/**/Boot/**/*.log",
            "**/Beckhoff/**/*.log",
            
            # Common CNC log locations
            "**/CNC/**/*.log",
            "**/logs/cnc*.log",
            "**/temp/cnc*.log",
        ]
        
        # Find existing log files
        log_files = []
        for base_path in self.reichenbacher_paths + self.twincat_paths:
            if os.path.exists(base_path):
                try:
                    for root, dirs, files in os.walk(base_path):
                        for file in files:
                            if file.lower().endswith(('.log', '.txt')) and any(
                                keyword in file.lower() for keyword in ['cnc', 'program', 'cycle', 'job', 'run']):
                                log_files.append(os.path.join(root, file))
                except PermissionError:
                    pass
                    
        print(f"📋 Monitoring {len(log_files)} CNC log files")
        
        # Monitor log files for changes
        last_sizes = {}
        
        while self.running:
            for log_file in log_files:
                try:
                    if os.path.exists(log_file):
                        current_size = os.path.getsize(log_file)
                        last_size = last_sizes.get(log_file, 0)
                        
                        if current_size > last_size:
                            # File has grown - read new content
                            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                                f.seek(last_size)
                                new_content = f.read()
                                
                                # Look for execution indicators
                                execution_keywords = ['field1', 'field33', 'start', 'run', 'cycle', 'execute', 'program']
                                if any(keyword in new_content.lower() for keyword in execution_keywords):
                                    self._log_detection('cnc_logs', 
                                                      f"Log activity in {os.path.basename(log_file)}: execution detected")
                                    
                        last_sizes[log_file] = current_size
                        
                except Exception as e:
                    pass  # Ignore file access errors
                    
            time.sleep(10)  # Check every 10 seconds
            
    def _monitor_databases_registry(self):
        """Monitor databases and registry for CNC execution data"""
        
        # Registry monitoring
        registry_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Reichenbacher"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Beckhoff"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Reichenbacher"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\HOPS"),
        ]
        
        # Database file patterns
        db_patterns = [
            "**/HOPS**/**/*.db",
            "**/HOPS**/**/*.sqlite",
            "**/RB_CNC**/**/*.db",
            "**/TwinCAT**/**/*.db",
            "**/Beckhoff**/**/*.db",
        ]
        
        # Find database files
        db_files = []
        for base_path in self.reichenbacher_paths + self.twincat_paths:
            if os.path.exists(base_path):
                try:
                    for root, dirs, files in os.walk(base_path):
                        for file in files:
                            if file.lower().endswith(('.db', '.sqlite', '.sqlite3')):
                                db_files.append(os.path.join(root, file))
                except PermissionError:
                    pass
                    
        print(f"💾 Monitoring {len(db_files)} database files")
        
        last_db_sizes = {}
        
        while self.running:
            # Monitor registry changes (simplified check)
            for hkey, subkey in registry_keys:
                try:
                    with winreg.OpenKey(hkey, subkey) as key:
                        # Check for execution-related values
                        for i in range(winreg.QueryInfoKey(key)[1]):
                            try:
                                value_name, value_data, _ = winreg.EnumValue(key, i)
                                if any(keyword in value_name.lower() 
                                      for keyword in ['last', 'current', 'count', 'cycle']):
                                    # Registry value that might indicate execution
                                    pass
                            except WindowsError:
                                pass
                except WindowsError:
                    pass
                    
            # Monitor database file changes
            for db_file in db_files:
                try:
                    if os.path.exists(db_file):
                        current_size = os.path.getsize(db_file)
                        last_size = last_db_sizes.get(db_file, 0)
                        
                        if current_size != last_size:
                            self._log_detection('database', 
                                              f"Database activity: {os.path.basename(db_file)} size changed")
                            
                        last_db_sizes[db_file] = current_size
                        
                except Exception as e:
                    pass
                    
            time.sleep(30)  # Check every 30 seconds
            
    def _monitor_power_patterns(self):
        """Monitor power consumption patterns via CPU usage"""
        
        # Find CNC/TwinCAT processes
        target_processes = []
        
        while self.running:
            current_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    proc_name = proc.info['name'].lower()
                    if any(keyword in proc_name for keyword in 
                          ['twincat', 'beckhoff', 'hops', 'cnc', 'reichenbacher']):
                        current_processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                    
            # Monitor CPU patterns for cyclical behavior
            if current_processes:
                total_cpu = 0
                high_activity_processes = []
                
                for proc in current_processes:
                    try:
                        cpu_percent = proc.cpu_percent(interval=1.0)
                        total_cpu += cpu_percent
                        
                        if cpu_percent > 30:  # High CPU = potential machining
                            high_activity_processes.append((proc.info['name'], cpu_percent))
                            
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                        
                # Detect patterns that suggest machining cycles
                if total_cpu > 50:  # High total CPU
                    self._log_detection('power', 
                                      f"High power pattern detected: {total_cpu:.1f}% total CPU")
                    
                if high_activity_processes:
                    for name, cpu in high_activity_processes:
                        self._log_detection('power', 
                                          f"Process power spike: {name} at {cpu:.1f}% CPU")
                        
            time.sleep(5)  # Check every 5 seconds
            
    def _log_detection(self, method, details):
        """Log a detection event"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        detection = {
            'timestamp': timestamp,
            'method': method,
            'details': details
        }
        
        self.detection_log.append(detection)
        self.detections[method] += 1
        
        # Keep only last 1000 detections
        if len(self.detection_log) > 1000:
            self.detection_log = self.detection_log[-1000:]
            
        print(f"🔍 [{timestamp}] {method.upper()}: {details}")
        
    def get_detection_summary(self):
        """Get summary of all detections"""
        return {
            'total_detections': len(self.detection_log),
            'detections_by_method': self.detections.copy(),
            'recent_detections': self.detection_log[-10:] if self.detection_log else []
        }
        
    def save_detection_log(self, filename="reichenbacher_detections.json"):
        """Save detection log to file"""
        data = {
            'machine': 'Reichenbacher Opus',
            'controller': 'Beckhoff TwinCAT',
            'generated': datetime.now().isoformat(),
            'summary': self.get_detection_summary(),
            'full_log': self.detection_log
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
            
        print(f"💾 Detection log saved: {filename}")
        
    def stop_monitoring(self):
        """Stop all monitoring"""
        self.running = False
        print("🛑 Reichenbacher serial work detection stopped")

def main():
    print("Reichenbacher Opus Serial Work Detector")
    print("Specialized for Reichenbacher machines with Beckhoff TwinCAT")
    print("=" * 60)
    
    detector = ReichenbacherSerialDetector()
    
    print("🚀 Starting all detection methods...")
    detection_threads = detector.start_all_detection_methods()
    
    print("\n🧪 Testing Instructions:")
    print("1. Start TwinCAT XAE and run a project")
    print("2. Access/modify Field1.nc file")
    print("3. Run any CNC programs if possible")
    print("4. Check output for detection events")
    print("\nPress Ctrl+C to stop and save results...")
    
    try:
        while True:
            time.sleep(10)
            summary = detector.get_detection_summary()
            if summary['total_detections'] > 0:
                print(f"\n📊 Detection Summary: {summary['total_detections']} total events")
                for method, count in summary['detections_by_method'].items():
                    if count > 0:
                        print(f"   {method}: {count} detections")
                        
    except KeyboardInterrupt:
        print("\n🛑 Stopping detector...")
        detector.stop_monitoring()
        detector.save_detection_log()
        
        print("\n📋 Final Summary:")
        summary = detector.get_detection_summary()
        print(f"Total detections: {summary['total_detections']}")
        for method, count in summary['detections_by_method'].items():
            success_rate = "High" if count > 5 else "Medium" if count > 0 else "Low"
            print(f"  {method}: {count} events ({success_rate} success rate)")

if __name__ == "__main__":
    main()