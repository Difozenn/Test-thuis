#!/usr/bin/env python3
"""
TwinCAT Path Discovery
Automatically finds TwinCAT installations on any machine
"""

import os
import glob
import winreg
from pathlib import Path

class TwinCATPathDiscovery:
    def __init__(self):
        self.found_paths = []
        self.registry_paths = []
        self.file_system_paths = []
        
    def discover_all_paths(self):
        """Discover all TwinCAT paths on the system"""
        print("🔍 Discovering TwinCAT installations...")
        
        # Method 1: Registry search
        self.search_registry()
        
        # Method 2: File system search
        self.search_file_system()
        
        # Method 3: Process-based search
        self.search_running_processes()
        
        # Combine and deduplicate
        all_paths = list(set(self.registry_paths + self.file_system_paths))
        
        # Verify paths exist
        self.found_paths = [path for path in all_paths if os.path.exists(path)]
        
        return self.found_paths
        
    def search_registry(self):
        """Search Windows registry for TwinCAT installations"""
        print("  📋 Searching Windows Registry...")
        
        registry_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Beckhoff"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Beckhoff"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\TwinCAT"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Beckhoff"),
        ]
        
        for hkey, subkey in registry_keys:
            try:
                with winreg.OpenKey(hkey, subkey) as key:
                    # Enumerate subkeys
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as subkey_handle:
                                # Look for installation paths
                                for j in range(winreg.QueryInfoKey(subkey_handle)[1]):
                                    try:
                                        value_name, value_data, _ = winreg.EnumValue(subkey_handle, j)
                                        if 'path' in value_name.lower() or 'dir' in value_name.lower():
                                            if isinstance(value_data, str) and os.path.exists(value_data):
                                                self.registry_paths.append(value_data)
                                                print(f"    ✅ Registry: {value_data}")
                                    except WindowsError:
                                        pass
                        except WindowsError:
                            pass
            except WindowsError:
                pass
                
    def search_file_system(self):
        """Search file system for TwinCAT directories"""
        print("  📁 Searching File System...")
        
        # Common drive letters
        drives = ['C:', 'D:', 'E:', 'F:']
        
        # Search patterns
        search_patterns = [
            r"\TwinCAT*",
            r"\Beckhoff*", 
            r"\TC*",
            r"\CNC\*TwinCAT*",
            r"\Machine\*TwinCAT*",
            r"\Control\*TwinCAT*",
        ]
        
        for drive in drives:
            if os.path.exists(drive):
                print(f"    🔍 Scanning {drive}")
                
                # Direct TwinCAT searches
                for pattern in search_patterns:
                    try:
                        matches = glob.glob(drive + pattern)
                        for match in matches:
                            if os.path.isdir(match):
                                self.file_system_paths.append(match)
                                print(f"    ✅ Found: {match}")
                    except:
                        pass
                        
                # Search Program Files
                program_files = [
                    os.path.join(drive, "Program Files"),
                    os.path.join(drive, "Program Files (x86)"),
                ]
                
                for pf_dir in program_files:
                    if os.path.exists(pf_dir):
                        try:
                            for item in os.listdir(pf_dir):
                                if any(keyword in item.lower() for keyword in ['beckhoff', 'twincat']):
                                    full_path = os.path.join(pf_dir, item)
                                    if os.path.isdir(full_path):
                                        self.file_system_paths.append(full_path)
                                        print(f"    ✅ Program Files: {full_path}")
                        except PermissionError:
                            pass
                            
    def search_running_processes(self):
        """Search running processes for TwinCAT paths"""
        print("  🔄 Analyzing Running Processes...")
        
        try:
            import psutil
            
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    if proc.info['exe']:
                        exe_path = proc.info['exe'].lower()
                        if any(keyword in exe_path for keyword in ['twincat', 'beckhoff', 'tc3']):
                            # Extract directory from executable path
                            directory = os.path.dirname(proc.info['exe'])
                            
                            # Go up directories to find TwinCAT root
                            current_dir = directory
                            for _ in range(5):  # Search up to 5 levels
                                if 'twincat' in os.path.basename(current_dir).lower():
                                    self.file_system_paths.append(current_dir)
                                    print(f"    ✅ Process path: {current_dir}")
                                    break
                                current_dir = os.path.dirname(current_dir)
                                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                    
        except ImportError:
            print("    ⚠️  psutil not available for process search")
            
    def get_monitoring_paths(self):
        """Get specific paths to monitor"""
        monitoring_paths = []
        
        for base_path in self.found_paths:
            # Add common subdirectories
            subdirs = [
                "",  # Base directory
                "Target",
                "Boot", 
                "Config",
                "3.1\\Target",
                "3.1\\Boot",
                "3.1\\Config",
                "2.11\\Target",
                "2.11\\Boot",
                "Runtime",
                "Logs",
            ]
            
            for subdir in subdirs:
                full_path = os.path.join(base_path, subdir)
                if os.path.exists(full_path):
                    monitoring_paths.append(full_path)
                    
        return list(set(monitoring_paths))
        
    def generate_path_config(self, output_file="twincat_paths.txt"):
        """Generate configuration file with discovered paths"""
        if not self.found_paths:
            print("❌ No TwinCAT paths found")
            return
            
        with open(output_file, 'w') as f:
            f.write("# TwinCAT Paths Discovery Results\n")
            f.write(f"# Generated: {os.path.getctime}\n\n")
            
            f.write("# Base TwinCAT Installations:\n")
            for path in self.found_paths:
                f.write(f"{path}\n")
                
            f.write("\n# Monitoring Paths:\n")
            for path in self.get_monitoring_paths():
                f.write(f"{path}\n")
                
        print(f"📄 Configuration saved to: {output_file}")
        
    def print_summary(self):
        """Print discovery summary"""
        print(f"\n📊 TwinCAT Discovery Summary")
        print("=" * 40)
        print(f"Total installations found: {len(self.found_paths)}")
        print(f"Registry entries: {len(self.registry_paths)}")
        print(f"File system finds: {len(self.file_system_paths)}")
        
        if self.found_paths:
            print(f"\n✅ TwinCAT installations:")
            for i, path in enumerate(self.found_paths, 1):
                print(f"  {i}. {path}")
                
            monitoring_paths = self.get_monitoring_paths()
            print(f"\n👀 Recommended monitoring paths ({len(monitoring_paths)}):")
            for path in monitoring_paths[:10]:  # Show first 10
                print(f"  📁 {path}")
            if len(monitoring_paths) > 10:
                print(f"  ... and {len(monitoring_paths) - 10} more")
                
        else:
            print("\n❌ No TwinCAT installations found")
            print("💡 This might mean:")
            print("   - TwinCAT is not installed")
            print("   - Running with insufficient permissions")
            print("   - TwinCAT is installed in a non-standard location")

def main():
    print("TwinCAT Path Discovery Tool")
    print("=" * 40)
    
    discovery = TwinCATPathDiscovery()
    paths = discovery.discover_all_paths()
    
    discovery.print_summary()
    
    if paths:
        discovery.generate_path_config()
        print(f"\n💡 Use these paths in your monitoring scripts:")
        print("   Copy the paths from twincat_paths.txt")
        print("   Update TwinCAT_File_Monitor.py with the found paths")
    else:
        print(f"\n🔧 Troubleshooting:")
        print("   1. Make sure TwinCAT is installed")
        print("   2. Try running as Administrator")
        print("   3. Check if TwinCAT Runtime is on a different drive")

if __name__ == "__main__":
    main()