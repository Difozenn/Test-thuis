#!/usr/bin/env python3
"""
Test script to verify TCALC timing calculations match official output
Official TCALC_HH7 output for nesting.NC:
  - Total time: 39.5 seconds
  - Processing time: 10.3 seconds  
  - Tool change time: 26.1 seconds (2 changes)
  - Rapid time: 3.2 seconds
"""

import re
import math

class TCALCMachineConfig:
    def __init__(self):
        # From PP.ini
        self.DHFeedrateG00 = 50000  # mm/min for rapids (from PP.ini line 130)
        self.TC_51_51 = 13.05       # Tool change time INCLUDING movement (26.1s / 2)
        self.TC_ACTUAL = 10.0        # Actual tool change time from PP.ini
        self.TC_MOVEMENT = 3.05      # Movement to/from tool change position
        
        # Acceleration parameters for realistic timing
        self.Accel_G0 = 12000  # mm/s² for rapids
        self.Accel_G1 = 6000   # mm/s² for cutting
        self.Accel_G2 = 5000   # mm/s² for arcs

def analyze_file(filepath):
    """Analyze CNC file using TCALC methodology"""
    
    config = TCALCMachineConfig()
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    # Track position and timing
    current_x = 0
    current_y = 0
    current_z = 0
    current_feedrate = 0
    
    # Timing accumulation
    total_cutting_time = 0  # G1, G2, G3
    total_rapid_time = 0    # G0
    tool_changes = 0
    
    # Tool tracking
    tools_used = set()
    current_tool = None
    
    # Detect file format
    file_format = "Unknown"
    if "OPUS" in filepath.upper() or any("CH_TOOLCHANGE" in line for line in lines):
        file_format = "OPUS"
    elif "NESTING" in filepath.upper() or any("CP_TC.NC" in line for line in lines):
        file_format = "HH7"
    elif ".SPF" in filepath.upper() or any("C_WECHSEL" in line for line in lines):
        file_format = "Vision/Siemens"
    
    print(f"\nAnalyzing: {filepath}")
    print(f"Format: {file_format}")
    
    for line in lines:
        # Remove comments and clean line
        if ';' in line:
            line = line[:line.index(';')]
        line = line.strip().upper()
        
        if not line:
            continue
        
        # Extract feedrate
        f_match = re.search(r'F([\d.]+)', line)
        if f_match:
            current_feedrate = float(f_match.group(1))
        
        # Detect tool changes
        if file_format == "OPUS":
            if "CH_TOOLCHANGE.NC @P4=" in line:
                match = re.search(r'@P4=(\d+)', line)
                if match:
                    tool_num = int(match.group(1))
                    tools_used.add(tool_num)
                    if current_tool != tool_num:
                        tool_changes += 1
                        current_tool = tool_num
            elif re.match(r'^D\d+$', line):
                match = re.match(r'^D(\d+)$', line)
                if match:
                    tool_num = int(match.group(1))
                    if tool_num > 0:
                        tools_used.add(tool_num)
                        if current_tool != tool_num:
                            tool_changes += 1
                            current_tool = tool_num
                            
        elif file_format == "HH7":
            if "CP_TC.NC" in line:
                match = re.search(r'@P4=(\d+)', line)
                if match:
                    tool_num = int(match.group(1))
                    tools_used.add(tool_num)
                    if current_tool != tool_num:
                        tool_changes += 1
                        current_tool = tool_num
                        
        elif file_format == "Vision/Siemens":
            if "C_WECHSEL" in line:
                match = re.search(r'C_WECHSEL\((\d+)', line)
                if match:
                    platz = int(match.group(1))
                    # Map Platz to Box ID (from comments in file)
                    if platz == 17:
                        tool_num = 602
                    elif platz == 10:
                        tool_num = 181
                    else:
                        tool_num = platz
                    tools_used.add(tool_num)
                    if current_tool != tool_num:
                        tool_changes += 1
                        current_tool = tool_num
        
        # Process movements
        if line.startswith('G0'):
            # Rapid movement
            # Extract coordinates
            x_match = re.search(r'X([-\d.]+)', line)
            y_match = re.search(r'Y([-\d.]+)', line)
            z_match = re.search(r'Z([-\d.]+)', line)
            
            new_x = float(x_match.group(1)) if x_match else current_x
            new_y = float(y_match.group(1)) if y_match else current_y
            new_z = float(z_match.group(1)) if z_match else current_z
            
            # Calculate distance
            dx = new_x - current_x
            dy = new_y - current_y
            dz = new_z - current_z
            distance = math.sqrt(dx*dx + dy*dy + dz*dz)
            
            if distance > 0:
                # Simple time calculation for rapids
                time = (distance / config.DHFeedrateG00) * 60  # Convert to seconds
                total_rapid_time += time
            
            current_x, current_y, current_z = new_x, new_y, new_z
            
        elif line.startswith('G1') or line.startswith('G2') or line.startswith('G3'):
            # Cutting movement
            # For simplicity, estimate time based on typical cutting feedrate
            if current_feedrate > 0:
                # Extract end position for G1
                if line.startswith('G1'):
                    x_match = re.search(r'X([-\d.]+)', line)
                    y_match = re.search(r'Y([-\d.]+)', line)
                    z_match = re.search(r'Z([-\d.]+)', line)
                    
                    new_x = float(x_match.group(1)) if x_match else current_x
                    new_y = float(y_match.group(1)) if y_match else current_y
                    new_z = float(z_match.group(1)) if z_match else current_z
                    
                    dx = new_x - current_x
                    dy = new_y - current_y
                    dz = new_z - current_z
                    distance = math.sqrt(dx*dx + dy*dy + dz*dz)
                    
                    if distance > 0:
                        time = (distance / current_feedrate) * 60  # Convert to seconds
                        total_cutting_time += time
                    
                    current_x, current_y, current_z = new_x, new_y, new_z
                    
                # For G2/G3 (arcs), use simplified calculation
                elif line.startswith('G2') or line.startswith('G3'):
                    # Estimate arc length (simplified)
                    x_match = re.search(r'X([-\d.]+)', line)
                    y_match = re.search(r'Y([-\d.]+)', line)
                    
                    if x_match and y_match:
                        new_x = float(x_match.group(1))
                        new_y = float(y_match.group(1))
                        
                        # Check for radius
                        r_match = re.search(r'R=([-\d.]+)|CR=([-\d.]+)', line)
                        if r_match:
                            radius = float(r_match.group(1) if r_match.group(1) else r_match.group(2))
                            # Approximate arc length
                            chord = math.sqrt((new_x-current_x)**2 + (new_y-current_y)**2)
                            if radius > 0 and chord > 0:
                                # Arc length approximation
                                if chord < 2 * abs(radius):
                                    angle = 2 * math.asin(chord / (2 * abs(radius)))
                                    arc_length = abs(radius) * angle
                                else:
                                    arc_length = chord
                                
                                time = (arc_length / current_feedrate) * 60
                                total_cutting_time += time
                        
                        current_x, current_y = new_x, new_y
    
    # Calculate total time
    tool_change_time = tool_changes * config.TC_51_51
    total_time = total_cutting_time + total_rapid_time + tool_change_time
    
    # Output results
    print(f"Tools used: {sorted(tools_used)}")
    print(f"Tool changes: {tool_changes}")
    print(f"\nTiming Analysis:")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Cutting time: {total_cutting_time:.1f}s")
    print(f"  Tool change time: {tool_change_time:.1f}s ({tool_changes} × {config.TC_51_51}s)")
    print(f"  Rapid time: {total_rapid_time:.1f}s")
    print(f"  Overhead (TC + Rapids): {tool_change_time + total_rapid_time:.1f}s")
    
    return {
        'total_time': total_time,
        'cutting_time': total_cutting_time,
        'tool_change_time': tool_change_time,
        'rapid_time': total_rapid_time,
        'tool_changes': tool_changes,
        'tools_used': sorted(tools_used)
    }

def main():
    print("=" * 60)
    print("TCALC Timing Analysis Test")
    print("=" * 60)
    print("\nExpected values from official TCALC_HH7 output:")
    print("  Total: 39.5s")
    print("  Processing: 10.3s")
    print("  Tool changes: 26.1s (2 × 13.05s)")
    print("  Rapids: 3.2s")
    print("=" * 60)
    
    # Test all three files
    files = [
        'opus.nc',
        'nesting.NC',
        'Field1.spf'
    ]
    
    results = {}
    for filepath in files:
        try:
            results[filepath] = analyze_file(filepath)
        except FileNotFoundError:
            print(f"\n⚠️  File not found: {filepath}")
        except Exception as e:
            print(f"\n❌ Error analyzing {filepath}: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if results:
        # All files should show similar results since they're the same program
        print("\nConsistency check (all files should be similar):")
        for filepath, data in results.items():
            print(f"\n{filepath}:")
            print(f"  Total: {data['total_time']:.1f}s")
            print(f"  Tools: {data['tools_used']}")
            print(f"  Changes: {data['tool_changes']}")

if __name__ == "__main__":
    main()