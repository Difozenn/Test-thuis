#!/usr/bin/env python3
"""
TwinCAT Auto Monitor
Automatically discovers TwinCAT paths and starts monitoring
No manual editing required!
"""

import os
import sys
import time
import threading
from datetime import datetime

# Import our path discovery
try:
    from TwinCAT_Path_Discovery import TwinCATPathDiscovery
    PATH_DISCOVERY_AVAILABLE = True
except ImportError:
    PATH_DISCOVERY_AVAILABLE = False

class TwinCATAutoMonitor:
    def __init__(self):
        self.discovered_paths = []
        self.active_monitors = []
        self.running = False
        self.ads_net_id = '127.0.0.1.1.1'
        self.ads_port = 851
        
    def auto_discover_and_setup(self):
        """Automatically discover TwinCAT and setup monitoring"""
        print("🚀 TwinCAT Auto Monitor - No Manual Configuration Required!")
        print("=" * 60)
        
        # Step 1: Auto-discover TwinCAT paths
        if PATH_DISCOVERY_AVAILABLE:
            print("🔍 Auto-discovering TwinCAT installations...")
            discovery = TwinCATPathDiscovery()
            self.discovered_paths = discovery.discover_all_paths()
            
            if self.discovered_paths:
                print(f"✅ Found {len(self.discovered_paths)} TwinCAT installation(s)")
                for i, path in enumerate(self.discovered_paths, 1):
                    print(f"   {i}. {path}")
            else:
                print("❌ No TwinCAT installations found")
                return False
        else:
            print("⚠️  Path discovery not available - using default paths")
            self.discovered_paths = self._get_default_paths()
            
        # Step 2: Auto-setup monitoring with discovered paths
        return self._setup_monitoring_with_paths()
        
    def _get_default_paths(self):
        """Fallback default paths if discovery fails"""
        default_paths = [
            "C:\\TwinCAT\\",
            "D:\\TwinCAT\\", 
            "C:\\Program Files\\Beckhoff\\",
            "C:\\Program Files (x86)\\Beckhoff\\",
            "C:\\ProgramData\\Beckhoff\\",
        ]
        
        existing_paths = [path for path in default_paths if os.path.exists(path)]
        
        if existing_paths:
            print(f"✅ Using default paths: {len(existing_paths)} found")
            for path in existing_paths:
                print(f"   📁 {path}")
        else:
            print("❌ No default TwinCAT paths found")
            
        return existing_paths
        
    def _setup_monitoring_with_paths(self):
        """Setup monitoring using discovered paths"""
        if not self.discovered_paths:
            return False
            
        print("\n🛠️  Setting up monitoring...")
        
        # Test ADS monitoring
        ads_working = self._test_ads_monitoring()
        
        # Setup process monitoring  
        process_working = self._setup_process_monitoring()
        
        # Setup file monitoring with discovered paths
        file_working = self._setup_file_monitoring()
        
        active_methods = []
        if ads_working:
            active_methods.append("ADS")
        if process_working:
            active_methods.append("Process")
        if file_working:
            active_methods.append("File")
            
        if active_methods:
            print(f"✅ Active monitoring: {', '.join(active_methods)}")
            return True
        else:
            print("❌ No monitoring methods could be activated")
            return False
            
    def _test_ads_monitoring(self):
        """Test ADS monitoring with auto-discovery"""
        try:
            import pyads
            print("  📡 Testing ADS connection...")
            
            # Import enhanced ADS discovery
            try:
                from TwinCAT_ADS_Enhanced import TwinCATADSEnhanced
                enhanced = TwinCATADSEnhanced()
                
                # Try auto-discovery first
                if enhanced.find_working_connection():
                    self.ads_net_id = enhanced.ams_net_id
                    self.ads_port = enhanced.port
                    print(f"  ✅ ADS monitoring available at {self.ads_net_id}:{self.ads_port}")
                    return True
                else:
                    # Fallback to localhost
                    print("  ⚠️  Auto-discovery failed, trying localhost...")
                    
            except ImportError:
                print("  ⚠️  Enhanced ADS not available, using defaults...")
            
            # Fallback to default localhost
            connection = pyads.Connection('127.0.0.1.1.1', 851)
            connection.open()
            ads_state = connection.read_state()
            connection.close()
            
            self.ads_net_id = '127.0.0.1.1.1'
            self.ads_port = 851
            print("  ✅ ADS monitoring available (localhost)")
            return True
            
        except Exception as e:
            print(f"  ❌ ADS not available: {e}")
            return False
            
    def _setup_process_monitoring(self):
        """Setup process monitoring"""
        try:
            import psutil
            print("  🔍 Setting up process monitoring...")
            
            # Find TwinCAT processes
            twincat_processes = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if any(keyword in proc.info['name'].lower() 
                          for keyword in ['twincat', 'beckhoff', 'tc3']):
                        twincat_processes.append(proc.info['name'])
                except:
                    pass
                    
            if twincat_processes:
                print(f"  ✅ Process monitoring ready ({len(twincat_processes)} processes)")
                return True
            else:
                print("  ⚠️  No TwinCAT processes currently running")
                return True  # Still enable it for when processes start
                
        except Exception as e:
            print(f"  ❌ Process monitoring failed: {e}")
            return False
            
    def _setup_file_monitoring(self):
        """Setup file monitoring with discovered paths"""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            
            print("  📁 Setting up file monitoring...")
            
            # Get all monitoring subdirectories
            monitoring_paths = []
            for base_path in self.discovered_paths:
                subdirs = ["", "Target", "Boot", "Config", "3.1\\Target", "3.1\\Boot", "Logs"]
                for subdir in subdirs:
                    full_path = os.path.join(base_path, subdir)
                    if os.path.exists(full_path):
                        monitoring_paths.append(full_path)
                        
            if monitoring_paths:
                print(f"  ✅ File monitoring ready ({len(monitoring_paths)} paths)")
                return True
            else:
                print("  ❌ No valid paths for file monitoring")
                return False
                
        except Exception as e:
            print(f"  ❌ File monitoring failed: {e}")
            return False
            
    def start_monitoring(self):
        """Start all available monitoring"""
        if not self.discovered_paths:
            print("❌ No TwinCAT paths available - run auto_discover_and_setup() first")
            return False
            
        print("\n🚀 Starting Automatic TwinCAT Monitoring...")
        print("=" * 50)
        
        self.running = True
        
        # Start ADS monitoring
        self._start_ads_monitor()
        
        # Start process monitoring
        self._start_process_monitor()
        
        # Start file monitoring  
        self._start_file_monitor()
        
        print("✅ All monitoring started - watching for TwinCAT activity...")
        print("Press Ctrl+C to stop")
        
        return True
        
    def _start_ads_monitor(self):
        """Start ADS monitoring thread with discovered connection"""
        def ads_monitor():
            try:
                import pyads
                # Use discovered AMS Net ID and port
                connection = pyads.Connection(self.ads_net_id, self.ads_port)
                connection.open()
                
                last_state = None
                last_cycle_count = None
                
                while self.running:
                    try:
                        # Monitor state changes
                        ads_state = connection.read_state()
                        if ads_state[0] != last_state:
                            if ads_state[0] == pyads.ADSSTATE_RUN:
                                self._log_execution_event("ADS", f"TwinCAT Runtime RUNNING on {self.ads_net_id}")
                            last_state = ads_state[0]
                            
                        # Try to read cycle count if available
                        try:
                            for var_name in ["Main.nCycleCount", "MAIN.nCycleCount", "GVL.nCycleCount"]:
                                try:
                                    cycle_count = connection.read_by_name(var_name, pyads.PLCTYPE_ULINT)
                                    if cycle_count != last_cycle_count:
                                        self._log_execution_event("ADS", f"Cycle count: {cycle_count}")
                                        last_cycle_count = cycle_count
                                    break
                                except:
                                    pass
                        except:
                            pass
                            
                    except:
                        pass
                    time.sleep(1)
                    
                connection.close()
            except Exception as e:
                print(f"  ⚠️  ADS monitor error: {e}")
                
        thread = threading.Thread(target=ads_monitor, daemon=True)
        thread.start()
        
    def _start_process_monitor(self):
        """Start process monitoring thread"""
        def process_monitor():
            try:
                import psutil
                while self.running:
                    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                        try:
                            if any(keyword in proc.info['name'].lower() 
                                  for keyword in ['twincat', 'beckhoff']):
                                cpu = proc.cpu_percent(interval=0.1)
                                if cpu > 50:  # High CPU activity
                                    self._log_execution_event("Process", 
                                                            f"{proc.info['name']} high activity ({cpu:.1f}%)")
                        except:
                            pass
                    time.sleep(5)
            except:
                pass
                
        thread = threading.Thread(target=process_monitor, daemon=True)
        thread.start()
        
    def _start_file_monitor(self):
        """Start file monitoring thread"""
        def file_monitor():
            try:
                from watchdog.observers import Observer
                from watchdog.events import FileSystemEventHandler
                
                class TwinCATHandler(FileSystemEventHandler):
                    def __init__(self, callback):
                        self.callback = callback
                        
                    def on_modified(self, event):
                        if not event.is_directory:
                            if any(ext in event.src_path.lower() 
                                  for ext in ['.log', '.nc', '.prg']):
                                self.callback("File", f"Modified: {os.path.basename(event.src_path)}")
                
                observers = []
                for path in self.discovered_paths:
                    if os.path.exists(path):
                        observer = Observer()
                        handler = TwinCATHandler(self._log_execution_event)
                        observer.schedule(handler, path, recursive=True)
                        observer.start()
                        observers.append(observer)
                        
                while self.running:
                    time.sleep(1)
                    
                for observer in observers:
                    observer.stop()
                    observer.join()
                    
            except:
                pass
                
        thread = threading.Thread(target=file_monitor, daemon=True)
        thread.start()
        
    def _log_execution_event(self, source, details):
        """Log execution events"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"🚀 [{timestamp}] {source}: {details}")
        
        # Here you would integrate with your file monitor
        # self.notify_production_system(source, details)
        
    def stop_monitoring(self):
        """Stop all monitoring"""
        self.running = False
        print("🛑 Monitoring stopped")
        
    def run_interactive(self):
        """Run in interactive mode"""
        print("\n🎮 Interactive Mode Commands:")
        print("  'status' - Show monitoring status")
        print("  'paths' - Show discovered paths")  
        print("  'quit' - Exit")
        print()
        
        while self.running:
            try:
                cmd = input("AutoMonitor> ").strip().lower()
                
                if cmd == 'status':
                    print(f"Monitoring: {'Running' if self.running else 'Stopped'}")
                    print(f"TwinCAT paths: {len(self.discovered_paths)}")
                    
                elif cmd == 'paths':
                    print("Discovered TwinCAT paths:")
                    for i, path in enumerate(self.discovered_paths, 1):
                        print(f"  {i}. {path}")
                        
                elif cmd in ['quit', 'exit', 'q']:
                    break
                    
                else:
                    print("Unknown command")
                    
            except (EOFError, KeyboardInterrupt):
                break
                
        self.stop_monitoring()

def main():
    print("TwinCAT Auto Monitor - Zero Configuration Required!")
    print("Automatically discovers TwinCAT and starts monitoring")
    print()
    
    monitor = TwinCATAutoMonitor()
    
    # Auto-discover and setup
    if monitor.auto_discover_and_setup():
        # Start monitoring
        if monitor.start_monitoring():
            try:
                # Run until Ctrl+C
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Stopping monitor...")
                monitor.stop_monitoring()
        else:
            print("❌ Could not start monitoring")
    else:
        print("❌ Auto-discovery failed")
        print("\n💡 Troubleshooting:")
        print("   1. Make sure TwinCAT is installed")
        print("   2. Try running as Administrator") 
        print("   3. Install dependencies: pip install pyads watchdog psutil")

if __name__ == "__main__":
    main()