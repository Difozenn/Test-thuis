#!/usr/bin/env python3
"""
TwinCAT ADS Background Monitor
Tests ADS connection to local TwinCAT installation
"""

import time
import threading
import sys

try:
    import pyads
    ADS_AVAILABLE = True
except ImportError:
    ADS_AVAILABLE = False
    print("⚠️  pyads not installed. Install with: pip install pyads")

class TwinCATADSMonitor:
    def __init__(self, ams_net_id='127.0.0.1.1.1', port=851):
        self.ams_net_id = ams_net_id
        self.port = port
        self.running = False
        self.monitor_thread = None
        self.connection = None
        
    def test_ads_connection(self):
        """Test if we can connect to local TwinCAT"""
        if not ADS_AVAILABLE:
            return False
            
        try:
            print(f"🔍 Testing ADS connection to {self.ams_net_id}:{self.port}")
            self.connection = pyads.Connection(self.ams_net_id, self.port)
            self.connection.open()
            
            # Try to read ADS state
            ads_state = self.connection.read_state()
            print(f"✅ ADS Connection successful!")
            print(f"   ADS State: {ads_state[0]} (0=Invalid, 5=Run)")
            print(f"   Device State: {ads_state[1]}")
            
            # Try to read device info
            try:
                device_info = self.connection.read_device_info()
                print(f"   Device: {device_info.name}")
                print(f"   Version: {device_info.version}")
            except Exception as e:
                print(f"   Device info: {e}")
                
            return True
            
        except Exception as e:
            print(f"❌ ADS connection failed: {e}")
            print("   Make sure TwinCAT Runtime is running")
            return False
        finally:
            if self.connection:
                try:
                    self.connection.close()
                except:
                    pass
                    
    def start_background_monitoring(self):
        """Start background ADS monitoring"""
        if not ADS_AVAILABLE:
            print("❌ Cannot start ADS monitoring - pyads not available")
            return False
            
        if not self.test_ads_connection():
            return False
            
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("🔍 Background ADS monitoring started... Press Ctrl+C to stop")
        return True
        
    def _monitor_loop(self):
        """Main monitoring loop"""
        try:
            self.connection = pyads.Connection(self.ams_net_id, self.port)
            self.connection.open()
            
            last_state = None
            check_count = 0
            
            while self.running:
                try:
                    # Read ADS state
                    ads_state = self.connection.read_state()
                    current_state = ads_state[0]
                    
                    if current_state != last_state:
                        print(f"🔄 ADS State changed: {last_state} → {current_state}")
                        if current_state == pyads.ADSSTATE_RUN:
                            print("   ✅ TwinCAT Runtime is RUNNING")
                            self.on_twincat_running()
                        elif current_state == pyads.ADSSTATE_STOP:
                            print("   ⏹️  TwinCAT Runtime STOPPED")
                        last_state = current_state
                    
                    # Periodic status
                    check_count += 1
                    if check_count % 30 == 0:  # Every 30 seconds
                        print(f"📊 Monitoring active - State: {current_state} - Checks: {check_count}")
                        
                        # Try to read some system variables
                        try:
                            # These are standard TwinCAT system variables
                            sys_time = self.connection.read_by_name('SYSTEM.TIME', pyads.PLCTYPE_TIME)
                            print(f"   System Time: {sys_time}")
                        except Exception as e:
                            print(f"   System vars: {e}")
                    
                except Exception as e:
                    print(f"⚠️  Monitoring error: {e}")
                    
                time.sleep(1)  # Check every second
                
        except Exception as e:
            print(f"❌ Monitor loop error: {e}")
        finally:
            if self.connection:
                try:
                    self.connection.close()
                except:
                    pass
                    
    def on_twincat_running(self):
        """Called when TwinCAT runtime is detected as running"""
        print("🚀 TwinCAT Runtime Activity Detected!")
        # Here you would integrate with your file monitor
        # self.log_potential_execution()
        
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        print("🛑 ADS monitoring stopped")

def main():
    print("TwinCAT ADS Monitor Test")
    print("=" * 40)
    
    monitor = TwinCATADSMonitor()
    
    # Test connection first
    if monitor.test_ads_connection():
        print("\n" + "=" * 40)
        
        # Start monitoring
        if monitor.start_background_monitoring():
            try:
                # Keep running until Ctrl+C
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Stopping monitor...")
                monitor.stop_monitoring()
        else:
            print("❌ Could not start monitoring")
    else:
        print("\n💡 Tips for TwinCAT connection:")
        print("   1. Make sure TwinCAT XAE is running")
        print("   2. Start the local TwinCAT Runtime")
        print("   3. Check Windows Services for 'TwinCAT System Service'")
        print("   4. Try running as Administrator")

if __name__ == "__main__":
    main()