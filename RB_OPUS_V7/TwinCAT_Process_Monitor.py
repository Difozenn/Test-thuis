#!/usr/bin/env python3
"""
TwinCAT Process Monitor
Monitors TwinCAT processes and activity without ADS
"""

import psutil
import time
import threading
from datetime import datetime

class TwinCATProcessMonitor:
    def __init__(self):
        self.running = False
        self.monitor_thread = None
        self.twincat_processes = {}
        self.activity_threshold = 10.0  # CPU % threshold for activity
        
    def find_twincat_processes(self):
        """Find all TwinCAT related processes"""
        twincat_keywords = [
            'twincat', 'tc3', 'ads', 'beckhoff', 'tcadsrv', 'tcatssysmgr',
            'tcadswebservice', 'tcadsamslogger', 'tcatssysmgr', 'tcadsdll'
        ]
        
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'exe', 'memory_info', 'create_time']):
            try:
                proc_name = proc.info['name'].lower()
                proc_exe = (proc.info['exe'] or '').lower()
                
                # Check if any keyword matches
                if any(keyword in proc_name or keyword in proc_exe for keyword in twincat_keywords):
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'exe': proc.info['exe'],
                        'memory_mb': proc.info['memory_info'].rss / 1024 / 1024,
                        'started': datetime.fromtimestamp(proc.info['create_time']).strftime('%H:%M:%S'),
                        'process': proc
                    })
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
                
        return processes
        
    def get_process_activity(self, proc_info):
        """Get CPU and memory activity for a process"""
        try:
            proc = proc_info['process']
            
            # Get CPU percentage (requires time interval)
            cpu_percent = proc.cpu_percent(interval=0.1)
            
            # Get memory info
            memory_info = proc.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            # Get file handles (open files)
            try:
                open_files = len(proc.open_files())
            except psutil.AccessDenied:
                open_files = 0
                
            return {
                'cpu_percent': cpu_percent,
                'memory_mb': memory_mb,
                'open_files': open_files,
                'threads': proc.num_threads()
            }
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None
            
    def start_monitoring(self):
        """Start background process monitoring"""
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("🔍 TwinCAT Process monitoring started... Press Ctrl+C to stop")
        
    def _monitor_loop(self):
        """Main monitoring loop"""
        check_count = 0
        
        while self.running:
            try:
                # Find current TwinCAT processes
                current_processes = self.find_twincat_processes()
                
                if not current_processes:
                    if check_count % 30 == 0:  # Every 30 seconds
                        print("🔍 No TwinCAT processes found")
                else:
                    # Monitor each process
                    active_processes = []
                    total_cpu = 0
                    
                    for proc_info in current_processes:
                        activity = self.get_process_activity(proc_info)
                        
                        if activity:
                            total_cpu += activity['cpu_percent']
                            
                            # Check for high activity
                            if activity['cpu_percent'] > self.activity_threshold:
                                active_processes.append({
                                    'name': proc_info['name'],
                                    'cpu': activity['cpu_percent'],
                                    'memory': activity['memory_mb'],
                                    'files': activity['open_files']
                                })
                                
                    # Report activity
                    if active_processes:
                        print(f"🔥 High TwinCAT Activity Detected!")
                        for proc in active_processes:
                            print(f"   {proc['name']}: {proc['cpu']:.1f}% CPU, {proc['memory']:.1f}MB, {proc['files']} files")
                        self.on_high_activity(active_processes)
                        
                    # Periodic status
                    if check_count % 30 == 0:  # Every 30 seconds
                        print(f"📊 TwinCAT Processes: {len(current_processes)}, Total CPU: {total_cpu:.1f}%")
                        for proc in current_processes:
                            activity = self.get_process_activity(proc)
                            if activity:
                                print(f"   {proc['name']}: {activity['cpu_percent']:.1f}% CPU")
                
                check_count += 1
                time.sleep(1)  # Check every second
                
            except Exception as e:
                print(f"⚠️  Monitor error: {e}")
                time.sleep(5)
                
    def on_high_activity(self, active_processes):
        """Called when high TwinCAT activity is detected"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"🚀 [{timestamp}] Potential TwinCAT program execution!")
        
        # Here you would integrate with your file monitor
        # self.log_potential_execution()
        
    def stop_monitoring(self):
        """Stop monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        print("🛑 Process monitoring stopped")
        
    def print_system_overview(self):
        """Print current TwinCAT system overview"""
        print("\nTwinCAT System Overview")
        print("=" * 50)
        
        processes = self.find_twincat_processes()
        
        if not processes:
            print("❌ No TwinCAT processes found")
            print("\n💡 Tips:")
            print("   - Make sure TwinCAT is installed")
            print("   - Start TwinCAT XAE (Development Environment)")
            print("   - Check Windows Services for TwinCAT services")
            return
            
        print(f"✅ Found {len(processes)} TwinCAT processes:")
        print()
        
        for proc in processes:
            activity = self.get_process_activity(proc)
            print(f"📋 {proc['name']}")
            print(f"   PID: {proc['pid']}")
            print(f"   Started: {proc['started']}")
            print(f"   Memory: {proc['memory_mb']:.1f} MB")
            if activity:
                print(f"   CPU: {activity['cpu_percent']:.1f}%")
                print(f"   Threads: {activity['threads']}")
                print(f"   Open Files: {activity['open_files']}")
            print()

def main():
    print("TwinCAT Process Monitor Test")
    print("=" * 40)
    
    monitor = TwinCATProcessMonitor()
    
    # Show current system overview
    monitor.print_system_overview()
    
    print("=" * 40)
    
    # Start monitoring
    monitor.start_monitoring()
    
    try:
        # Keep running until Ctrl+C
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping monitor...")
        monitor.stop_monitoring()

if __name__ == "__main__":
    main()