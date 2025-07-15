#!/usr/bin/env python3
"""
TwinCAT Combined Monitor
Tests all monitoring methods and combines the best ones
"""

import time
import threading
import sys
import os
from datetime import datetime

# Import our monitoring classes
try:
    from TwinCAT_ADS_Monitor import TwinCATADSMonitor
    ADS_AVAILABLE = True
except ImportError:
    ADS_AVAILABLE = False

try:
    from TwinCAT_Process_Monitor import TwinCATProcessMonitor
    PROCESS_AVAILABLE = True
except ImportError:
    PROCESS_AVAILABLE = False

try:
    from TwinCAT_File_Monitor import TwinCATFileMonitor
    FILE_AVAILABLE = True
except ImportError:
    FILE_AVAILABLE = False

class TwinCATCombinedMonitor:
    def __init__(self):
        self.running = False
        self.ads_monitor = None
        self.process_monitor = None
        self.file_monitor = None
        
        self.execution_events = []
        
    def test_all_methods(self):
        """Test all available monitoring methods"""
        print("TwinCAT Combined Monitor - Testing All Methods")
        print("=" * 60)
        
        results = {
            'ads': False,
            'process': False,
            'file': False
        }
        
        # Test ADS
        if ADS_AVAILABLE:
            print("\n📡 Testing ADS Connection...")
            try:
                self.ads_monitor = TwinCATADSMonitor()
                results['ads'] = self.ads_monitor.test_ads_connection()
            except Exception as e:
                print(f"❌ ADS test error: {e}")
        else:
            print("\n📡 ADS monitoring not available (pyads not installed)")
            
        # Test Process Monitoring
        if PROCESS_AVAILABLE:
            print("\n🔍 Testing Process Monitoring...")
            try:
                self.process_monitor = TwinCATProcessMonitor()
                processes = self.process_monitor.find_twincat_processes()
                if processes:
                    print(f"✅ Found {len(processes)} TwinCAT processes")
                    results['process'] = True
                else:
                    print("❌ No TwinCAT processes found")
            except Exception as e:
                print(f"❌ Process test error: {e}")
        else:
            print("\n🔍 Process monitoring not available")
            
        # Test File Monitoring
        if FILE_AVAILABLE:
            print("\n📁 Testing File Monitoring...")
            try:
                self.file_monitor = TwinCATFileMonitor()
                paths = self.file_monitor.find_twincat_directories()
                if paths:
                    print(f"✅ Found {len(paths)} TwinCAT directories")
                    results['file'] = True
                else:
                    print("❌ No TwinCAT directories found")
            except Exception as e:
                print(f"❌ File test error: {e}")
        else:
            print("\n📁 File monitoring not available (watchdog not installed)")
            
        return results
        
    def start_best_available_monitoring(self):
        """Start the best available monitoring methods"""
        test_results = self.test_all_methods()
        
        print("\n" + "=" * 60)
        print("🚀 Starting Best Available Monitoring Methods")
        print("=" * 60)
        
        active_monitors = []
        
        # Start ADS if available
        if test_results['ads'] and self.ads_monitor:
            try:
                if self.ads_monitor.start_background_monitoring():
                    active_monitors.append("ADS")
                    print("✅ ADS monitoring started")
            except Exception as e:
                print(f"⚠️  ADS monitoring failed: {e}")
                
        # Start Process monitoring if available
        if test_results['process'] and self.process_monitor:
            try:
                self.process_monitor.start_monitoring()
                active_monitors.append("Process")
                print("✅ Process monitoring started")
            except Exception as e:
                print(f"⚠️  Process monitoring failed: {e}")
                
        # Start File monitoring if available
        if test_results['file'] and self.file_monitor:
            try:
                if self.file_monitor.start_monitoring():
                    active_monitors.append("File")
                    print("✅ File monitoring started")
            except Exception as e:
                print(f"⚠️  File monitoring failed: {e}")
                
        if active_monitors:
            print(f"\n🎯 Active monitoring: {', '.join(active_monitors)}")
            print("Watching for TwinCAT activity... Press Ctrl+C to stop")
            self.running = True
            return True
        else:
            print("\n❌ No monitoring methods could be started")
            return False
            
    def log_execution_event(self, source, details):
        """Log a potential execution event"""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        event = {
            'timestamp': timestamp,
            'source': source,
            'details': details
        }
        
        self.execution_events.append(event)
        
        # Keep only last 50 events
        if len(self.execution_events) > 50:
            self.execution_events = self.execution_events[-50:]
            
        print(f"🚀 [{timestamp}] EXECUTION EVENT from {source}: {details}")
        
        # Here you would integrate with your file monitor
        # self.notify_file_monitor(event)
        
    def show_execution_summary(self):
        """Show summary of detected execution events"""
        if not self.execution_events:
            print("📊 No execution events detected yet")
            return
            
        print(f"\n📊 Execution Events Summary ({len(self.execution_events)} events)")
        print("-" * 50)
        
        for event in self.execution_events[-10:]:  # Show last 10
            print(f"[{event['timestamp']}] {event['source']}: {event['details']}")
            
    def stop_all_monitoring(self):
        """Stop all active monitoring"""
        self.running = False
        
        if self.ads_monitor:
            try:
                self.ads_monitor.stop_monitoring()
            except:
                pass
                
        if self.process_monitor:
            try:
                self.process_monitor.stop_monitoring()
            except:
                pass
                
        if self.file_monitor:
            try:
                self.file_monitor.stop_monitoring()
            except:
                pass
                
        print("🛑 All monitoring stopped")
        
    def interactive_mode(self):
        """Interactive mode for testing"""
        print("\n🎮 Interactive Mode")
        print("Commands:")
        print("  'status' - Show current status")
        print("  'events' - Show recent execution events")
        print("  'test' - Re-test all methods")
        print("  'quit' - Exit")
        print()
        
        while self.running:
            try:
                cmd = input("Monitor> ").strip().lower()
                
                if cmd == 'status':
                    print(f"Running: {self.running}")
                    print(f"ADS: {'Active' if self.ads_monitor and self.ads_monitor.running else 'Inactive'}")
                    print(f"Process: {'Active' if self.process_monitor and self.process_monitor.running else 'Inactive'}")
                    print(f"File: {'Active' if self.file_monitor and self.file_monitor.running else 'Inactive'}")
                    
                elif cmd == 'events':
                    self.show_execution_summary()
                    
                elif cmd == 'test':
                    self.test_all_methods()
                    
                elif cmd in ['quit', 'exit', 'q']:
                    break
                    
                else:
                    print("Unknown command. Type 'quit' to exit.")
                    
            except (EOFError, KeyboardInterrupt):
                break
                
        self.stop_all_monitoring()

def main():
    print("TwinCAT Combined Monitor")
    print("Testing all available monitoring methods for your TwinCAT installation")
    print()
    
    monitor = TwinCATCombinedMonitor()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        # Interactive mode
        if monitor.start_best_available_monitoring():
            monitor.interactive_mode()
    else:
        # Automatic monitoring mode
        if monitor.start_best_available_monitoring():
            try:
                # Show periodic status
                while True:
                    time.sleep(30)  # Every 30 seconds
                    monitor.show_execution_summary()
                    
            except KeyboardInterrupt:
                print("\n🛑 Stopping all monitoring...")
                monitor.stop_all_monitoring()
        else:
            print("\n💡 Troubleshooting Tips:")
            print("   1. Install missing dependencies:")
            print("      pip install pyads watchdog psutil")
            print("   2. Make sure TwinCAT is installed and running")
            print("   3. Try running as Administrator")
            print("   4. Start TwinCAT XAE and create a simple project")
            print("\n   Run with --interactive for interactive testing:")
            print("   python TwinCAT_Combined_Monitor.py --interactive")

if __name__ == "__main__":
    main()