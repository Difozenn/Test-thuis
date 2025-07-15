#!/usr/bin/env python3
"""
TwinCAT File Monitor
Monitors TwinCAT directories for file activity
"""

import os
import time
import threading
from datetime import datetime
from pathlib import Path

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    print("⚠️  watchdog not installed. Install with: pip install watchdog")

class TwinCATFileHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback
        super().__init__()
        
    def on_modified(self, event):
        if not event.is_directory:
            self.callback('modified', event.src_path)
            
    def on_created(self, event):
        if not event.is_directory:
            self.callback('created', event.src_path)
            
    def on_deleted(self, event):
        if not event.is_directory:
            self.callback('deleted', event.src_path)

class TwinCATFileMonitor:
    def __init__(self):
        self.running = False
        self.observers = []
        self.activity_log = []
        
        # Common TwinCAT directories (adjust paths as needed)
        self.twincat_paths = [
            "C:\\TwinCAT\\3.1\\Target\\",
            "C:\\TwinCAT\\3.1\\Boot\\",
            "C:\\TwinCAT\\3.1\\Config\\",
            "C:\\ProgramData\\Beckhoff\\",
            "C:\\Users\\Public\\Documents\\Beckhoff\\",
            "C:\\TwinCAT\\",  # Your local installation
        ]
        
        # File extensions to monitor
        self.monitored_extensions = [
            '.log', '.nc', '.prg', '.exp', '.ads', '.tmc', '.tsproj', 
            '.plcproj', '.tpy', '.xml', '.cfg', '.ini'
        ]
        
    def find_twincat_directories(self):
        """Find existing TwinCAT directories"""
        existing_paths = []
        
        for path in self.twincat_paths:
            if os.path.exists(path):
                existing_paths.append(path)
                print(f"✅ Found TwinCAT directory: {path}")
            else:
                print(f"❌ Not found: {path}")
                
        # Also check for any Beckhoff directories
        possible_locations = [
            "C:\\Program Files\\Beckhoff\\",
            "C:\\Program Files (x86)\\Beckhoff\\",
        ]
        
        for location in possible_locations:
            if os.path.exists(location):
                for item in os.listdir(location):
                    full_path = os.path.join(location, item)
                    if os.path.isdir(full_path):
                        existing_paths.append(full_path)
                        print(f"✅ Found Beckhoff directory: {full_path}")
                        
        return existing_paths
        
    def is_interesting_file(self, file_path):
        """Check if file is worth monitoring"""
        file_path_lower = file_path.lower()
        
        # Check extension
        for ext in self.monitored_extensions:
            if file_path_lower.endswith(ext):
                return True
                
        # Check for specific TwinCAT files
        interesting_files = [
            'amslogger', 'tcadsrv', 'system', 'runtime', 'plc',
            'program', 'cycle', 'error', 'event'
        ]
        
        for keyword in interesting_files:
            if keyword in file_path_lower:
                return True
                
        return False
        
    def on_file_event(self, event_type, file_path):
        """Handle file system events"""
        if not self.is_interesting_file(file_path):
            return
            
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        filename = os.path.basename(file_path)
        
        print(f"📁 [{timestamp}] {event_type.upper()}: {filename}")
        print(f"   Path: {file_path}")
        
        # Log activity
        self.activity_log.append({
            'timestamp': timestamp,
            'event': event_type,
            'file': filename,
            'path': file_path
        })
        
        # Keep only last 100 events
        if len(self.activity_log) > 100:
            self.activity_log = self.activity_log[-100:]
            
        # Check for execution indicators
        if self.indicates_execution(file_path, event_type):
            self.on_execution_detected(file_path)
            
    def indicates_execution(self, file_path, event_type):
        """Check if file activity indicates program execution"""
        file_lower = file_path.lower()
        
        # Log file modifications often indicate activity
        if event_type == 'modified' and '.log' in file_lower:
            return True
            
        # Program files being accessed
        if '.nc' in file_lower or '.prg' in file_lower:
            return True
            
        # Runtime files
        if 'runtime' in file_lower or 'cycle' in file_lower:
            return True
            
        return False
        
    def on_execution_detected(self, file_path):
        """Called when potential execution is detected"""
        print(f"🚀 Potential execution detected from: {os.path.basename(file_path)}")
        # Here you would integrate with your file monitor
        
    def start_monitoring(self):
        """Start file monitoring"""
        if not WATCHDOG_AVAILABLE:
            print("❌ Cannot start file monitoring - watchdog not available")
            return False
            
        existing_paths = self.find_twincat_directories()
        
        if not existing_paths:
            print("❌ No TwinCAT directories found to monitor")
            return False
            
        print(f"\n🔍 Starting file monitoring on {len(existing_paths)} directories...")
        
        for path in existing_paths:
            try:
                observer = Observer()
                handler = TwinCATFileHandler(self.on_file_event)
                observer.schedule(handler, path, recursive=True)
                observer.start()
                self.observers.append(observer)
                print(f"👀 Monitoring: {path}")
            except Exception as e:
                print(f"⚠️  Could not monitor {path}: {e}")
                
        if self.observers:
            self.running = True
            print("✅ File monitoring started. Make changes to TwinCAT files to see activity...")
            return True
        else:
            print("❌ No directories could be monitored")
            return False
            
    def stop_monitoring(self):
        """Stop file monitoring"""
        self.running = False
        
        for observer in self.observers:
            observer.stop()
            observer.join()
            
        self.observers.clear()
        print("🛑 File monitoring stopped")
        
    def show_recent_activity(self):
        """Show recent file activity"""
        if not self.activity_log:
            print("📋 No recent activity")
            return
            
        print(f"\n📋 Recent Activity (last {len(self.activity_log)} events):")
        print("-" * 50)
        
        for event in self.activity_log[-10:]:  # Show last 10
            print(f"[{event['timestamp']}] {event['event'].upper()}: {event['file']}")
            
    def manual_directory_scan(self):
        """Manually scan directories for recent changes"""
        print("\n🔍 Manual directory scan...")
        
        existing_paths = self.find_twincat_directories()
        recent_files = []
        
        cutoff_time = time.time() - 3600  # Last hour
        
        for directory in existing_paths:
            try:
                for root, dirs, files in os.walk(directory):
                    for file in files:
                        if self.is_interesting_file(file):
                            file_path = os.path.join(root, file)
                            try:
                                mtime = os.path.getmtime(file_path)
                                if mtime > cutoff_time:
                                    recent_files.append({
                                        'path': file_path,
                                        'modified': datetime.fromtimestamp(mtime).strftime('%H:%M:%S'),
                                        'file': file
                                    })
                            except OSError:
                                pass
            except Exception as e:
                print(f"⚠️  Error scanning {directory}: {e}")
                
        if recent_files:
            print(f"📋 Found {len(recent_files)} recently modified files:")
            for file_info in sorted(recent_files, key=lambda x: x['modified'], reverse=True):
                print(f"   [{file_info['modified']}] {file_info['file']}")
        else:
            print("📋 No recently modified TwinCAT files found")

def main():
    print("TwinCAT File Monitor Test")
    print("=" * 40)
    
    monitor = TwinCATFileMonitor()
    
    # Manual scan first
    monitor.manual_directory_scan()
    
    print("\n" + "=" * 40)
    
    # Start monitoring
    if monitor.start_monitoring():
        try:
            while True:
                time.sleep(10)
                # Show recent activity every 10 seconds
                monitor.show_recent_activity()
        except KeyboardInterrupt:
            print("\n🛑 Stopping monitor...")
            monitor.stop_monitoring()
    else:
        print("💡 Tips:")
        print("   - Make sure TwinCAT is installed")
        print("   - Check if paths exist in your system")
        print("   - Try running as Administrator")

if __name__ == "__main__":
    main()