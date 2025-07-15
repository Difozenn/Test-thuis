#!/usr/bin/env python3
"""
Enhanced TwinCAT ADS Monitor with Auto-Discovery
Automatically finds AMS Net ID or allows manual configuration
"""

import os
import sys
import time
import socket
import struct
import winreg
from datetime import datetime

try:
    import pyads
    ADS_AVAILABLE = True
except ImportError:
    ADS_AVAILABLE = False
    print("⚠️  PyADS not installed. Install with: pip install pyads")

class TwinCATADSEnhanced:
    """Enhanced ADS monitor with auto-discovery"""
    
    def __init__(self):
        self.ams_net_id = None
        self.port = 851  # Default TwinCAT Runtime 1 port
        self.connection = None
        self.possible_ports = [851, 852, 853, 854]  # Runtime 1-4
        
    def auto_discover_ams_net_id(self):
        """Automatically discover AMS Net ID from multiple sources"""
        print("🔍 Auto-discovering TwinCAT AMS Net ID...")
        
        # Method 1: Try localhost (dev machine)
        localhost_ids = [
            '127.0.0.1.1.1',  # Common localhost
            '192.168.0.1.1.1',  # Common local network
        ]
        
        # Method 2: Read from registry
        registry_id = self._get_ams_from_registry()
        if registry_id:
            print(f"  📋 Registry AMS Net ID: {registry_id}")
            
        # Method 3: Read from TwinCAT config files
        file_ids = self._get_ams_from_config_files()
        for fid in file_ids:
            print(f"  📁 Config file AMS Net ID: {fid}")
            
        # Method 4: Network adapter IP-based
        adapter_ids = self._get_ams_from_network_adapters()
        for aid in adapter_ids:
            print(f"  🌐 Network adapter AMS Net ID: {aid}")
            
        # Combine all discovered IDs
        all_ids = localhost_ids + ([registry_id] if registry_id else []) + file_ids + adapter_ids
        unique_ids = list(dict.fromkeys(all_ids))  # Remove duplicates
        
        print(f"\n📋 Found {len(unique_ids)} potential AMS Net IDs to test")
        return unique_ids
        
    def _get_ams_from_registry(self):
        """Get AMS Net ID from Windows registry"""
        try:
            # TwinCAT 3 registry locations
            registry_paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Beckhoff\TwinCAT3\System"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Beckhoff\TwinCAT3\System"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Beckhoff\TwinCAT3\System"),
            ]
            
            for hkey, path in registry_paths:
                try:
                    with winreg.OpenKey(hkey, path) as key:
                        # Look for AmsNetId value
                        for i in range(winreg.QueryInfoKey(key)[1]):
                            try:
                                name, value, _ = winreg.EnumValue(key, i)
                                if 'amsnetid' in name.lower():
                                    return value
                            except:
                                pass
                except:
                    pass
                    
        except Exception as e:
            pass
            
        return None
        
    def _get_ams_from_config_files(self):
        """Get AMS Net IDs from TwinCAT config files"""
        ids = []
        
        # Common TwinCAT config locations
        config_paths = [
            r"C:\TwinCAT\3.1\Config\Io\TcSystemConfig.xml",
            r"C:\TwinCAT\Config\Io\TcSystemConfig.xml",
            r"C:\ProgramData\Beckhoff\TwinCAT\3.1\Config\Io\TcSystemConfig.xml",
        ]
        
        for path in config_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        content = f.read()
                        
                    # Look for AmsNetId in XML
                    import re
                    matches = re.findall(r'AmsNetId["\s=>]+([0-9.]+)', content)
                    ids.extend(matches)
                except:
                    pass
                    
        return ids
        
    def _get_ams_from_network_adapters(self):
        """Generate AMS Net IDs based on network adapter IPs"""
        ids = []
        
        try:
            # Get local IP addresses
            hostname = socket.gethostname()
            local_ips = socket.gethostbyname_ex(hostname)[2]
            
            # Convert IPs to AMS Net ID format (add .1.1)
            for ip in local_ips:
                if not ip.startswith('127.'):  # Skip localhost
                    ams_id = f"{ip}.1.1"
                    ids.append(ams_id)
                    
        except:
            pass
            
        return ids
        
    def test_ams_connection(self, ams_net_id, port=None):
        """Test connection to specific AMS Net ID"""
        if not ADS_AVAILABLE:
            return False
            
        test_port = port or self.port
        
        try:
            print(f"  🔌 Testing {ams_net_id}:{test_port}...", end='')
            
            # Set route (may be needed for remote connections)
            pyads.add_route(ams_net_id, ams_net_id.replace('.1.1', ''))
            
            # Try to connect
            connection = pyads.Connection(ams_net_id, test_port)
            connection.open()
            
            # Try to read state
            state = connection.read_state()
            connection.close()
            
            print(f" ✅ Connected! State: {state}")
            return True
            
        except Exception as e:
            print(f" ❌ Failed")
            return False
            
    def find_working_connection(self):
        """Find first working AMS Net ID and port combination"""
        # Get all potential IDs
        ams_ids = self.auto_discover_ams_net_id()
        
        print("\n🧪 Testing AMS connections...")
        
        # Test each ID with each port
        for ams_id in ams_ids:
            for port in self.possible_ports:
                if self.test_ams_connection(ams_id, port):
                    self.ams_net_id = ams_id
                    self.port = port
                    print(f"\n✅ Working connection found: {ams_id}:{port}")
                    return True
                    
        print("\n❌ No working ADS connection found")
        return False
        
    def manual_setup(self, ams_net_id, port=851):
        """Manually set AMS Net ID and port"""
        self.ams_net_id = ams_net_id
        self.port = port
        print(f"📡 Manual AMS setup: {ams_net_id}:{port}")
        
    def connect(self):
        """Connect to TwinCAT using discovered or manual settings"""
        if not self.ams_net_id:
            print("❌ No AMS Net ID configured. Run find_working_connection() first")
            return False
            
        try:
            self.connection = pyads.Connection(self.ams_net_id, self.port)
            self.connection.open()
            print(f"✅ Connected to {self.ams_net_id}:{self.port}")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
            
    def read_cycle_count(self, variable_name="Main.nCycleCount"):
        """Read cycle count or any other variable"""
        if not self.connection or not self.connection.is_open:
            print("❌ Not connected. Call connect() first")
            return None
            
        try:
            # Try to read as ULINT (64-bit unsigned)
            value = self.connection.read_by_name(variable_name, pyads.PLCTYPE_ULINT)
            return value
        except Exception as e:
            # Try as DINT (32-bit signed) if ULINT fails
            try:
                value = self.connection.read_by_name(variable_name, pyads.PLCTYPE_DINT)
                return value
            except:
                print(f"❌ Could not read {variable_name}: {e}")
                return None
                
    def monitor_cycle_count(self, variable_name="Main.nCycleCount", interval=1.0):
        """Monitor cycle count changes"""
        if not self.connection or not self.connection.is_open:
            print("❌ Not connected. Call connect() first")
            return
            
        print(f"👀 Monitoring {variable_name} every {interval}s...")
        print("Press Ctrl+C to stop\n")
        
        last_count = None
        
        try:
            while True:
                count = self.read_cycle_count(variable_name)
                
                if count is not None:
                    if last_count is None:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Initial count: {count}")
                    elif count != last_count:
                        diff = count - last_count
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Count changed: {count} (+{diff})")
                        
                    last_count = count
                    
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped")
            
    def disconnect(self):
        """Disconnect from TwinCAT"""
        if self.connection and self.connection.is_open:
            self.connection.close()
            print("🔌 Disconnected")

def main():
    print("Enhanced TwinCAT ADS Monitor")
    print("=" * 50)
    
    if not ADS_AVAILABLE:
        print("❌ PyADS not available. Install with: pip install pyads")
        return
        
    monitor = TwinCATADSEnhanced()
    
    # Check command line arguments
    if len(sys.argv) > 1:
        # Manual mode
        ams_net_id = sys.argv[1]
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 851
        
        print(f"📡 Using manual AMS Net ID: {ams_net_id}:{port}")
        monitor.manual_setup(ams_net_id, port)
        
        if monitor.connect():
            monitor.monitor_cycle_count()
            monitor.disconnect()
            
    else:
        # Auto-discovery mode
        print("🔍 Auto-discovery mode\n")
        
        if monitor.find_working_connection():
            print("\n💡 Connection successful!")
            print(f"   AMS Net ID: {monitor.ams_net_id}")
            print(f"   Port: {monitor.port}")
            print("\n📝 For future use, you can run:")
            print(f"   python {sys.argv[0]} {monitor.ams_net_id} {monitor.port}")
            
            if monitor.connect():
                # Try to read some standard variables
                print("\n🧪 Testing variable reads...")
                
                test_vars = [
                    "Main.nCycleCount",
                    "MAIN.nCycleCount", 
                    "GVL.nCycleCount",
                    "CycleCount",
                ]
                
                for var in test_vars:
                    value = monitor.read_cycle_count(var)
                    if value is not None:
                        print(f"✅ Found {var} = {value}")
                        monitor.monitor_cycle_count(var)
                        break
                else:
                    print("❌ No standard cycle count variables found")
                    print("💡 You may need to specify the exact variable name")
                    
                monitor.disconnect()
        else:
            print("\n💡 Troubleshooting:")
            print("1. Make sure TwinCAT is running")
            print("2. Check if ADS is enabled in TwinCAT")
            print("3. Try manual mode with your machine's AMS Net ID:")
            print(f"   python {sys.argv[0]} <AMS_NET_ID> [PORT]")
            print("   Example: python {sys.argv[0]} 192.168.1.100.1.1 851")

if __name__ == "__main__":
    main()