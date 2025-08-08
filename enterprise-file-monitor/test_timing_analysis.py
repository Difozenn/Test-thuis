#!/usr/bin/env python3
"""
Complete timing analysis for CNC files showing cycle time, cut time, and overhead time
"""

import re
import math

class CNCTimingAnalyzer:
    def __init__(self):
        # Machine configuration (matching TCALC defaults)
        self.rapid_feedrate = 40000  # mm/min (40m/min)
        self.tool_change_time = 15  # seconds per tool change
        self.spindle_start_time = 3  # seconds per spindle start
        self.cycle_overhead = 1  # seconds per L CYCLE call
        
        # Current position tracking
        self.current_x = 0
        self.current_y = 0
        self.current_z = 0
        self.current_feedrate = 0
        self.current_tool = 0
        
    def calculate_distance(self, x1, y1, z1, x2, y2, z2):
        """Calculate 3D distance between two points"""
        return math.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)
    
    def parse_coordinates(self, line):
        """Extract X, Y, Z coordinates from a line"""
        coords = {}
        
        # Look for X, Y, Z values
        x_match = re.search(r'X([-+]?\d*\.?\d+)', line)
        y_match = re.search(r'Y([-+]?\d*\.?\d+)', line)
        z_match = re.search(r'Z([-+]?\d*\.?\d+)', line)
        
        if x_match:
            coords['X'] = float(x_match.group(1))
        if y_match:
            coords['Y'] = float(y_match.group(1))
        if z_match:
            coords['Z'] = float(z_match.group(1))
            
        return coords
    
    def analyze_file(self, filename, description):
        """Analyze a CNC file for complete timing breakdown"""
        
        print(f"\n{'='*70}")
        print(f"FILE: {filename}")
        print(f"FORMAT: {description}")
        print(f"{'='*70}")
        
        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except:
            with open(filename, 'r', encoding='latin-1') as f:
                lines = f.readlines()
        
        # Timing accumulators
        rapid_time = 0  # G0 movements
        cut_time = 0    # G1, G2, G3 movements
        tool_changes = 0
        spindle_starts = 0
        cycle_calls = 0
        
        # Movement tracking
        movements = {'G0': 0, 'G1': 0, 'G2': 0, 'G3': 0}
        tool_change_lines = []
        
        # Reset position
        self.current_x = 0
        self.current_y = 0
        self.current_z = 0
        self.current_feedrate = 0
        self.current_tool = 0
        
        for i, line in enumerate(lines, 1):
            clean_line = line.split(';')[0].strip()
            if not clean_line:
                continue
            
            # Extract feedrate
            f_match = re.search(r'F([-+]?\d*\.?\d+)', clean_line)
            if f_match:
                self.current_feedrate = float(f_match.group(1))
            
            # Count tool changes
            tool_changed = False
            
            # OPUS format
            if "CH_TOOLCHANGE.NC" in line:
                match = re.search(r"@P4=(\d+)", line)
                if match:
                    new_tool = int(match.group(1))
                    if new_tool != self.current_tool:
                        tool_changes += 1
                        tool_change_lines.append(f"  Line {i}: CH_TOOLCHANGE to T{new_tool}")
                        self.current_tool = new_tool
                        tool_changed = True
            
            # HH7/Nesting format
            elif "CP_TC.NC" in line:
                match = re.search(r"@P4=(\d+)", line)
                if match:
                    new_tool = int(match.group(1))
                    if new_tool != self.current_tool:
                        tool_changes += 1
                        tool_change_lines.append(f"  Line {i}: CP_TC to T{new_tool}")
                        self.current_tool = new_tool
                        tool_changed = True
            
            # Vision/Siemens format
            elif "C_WECHSEL" in line:
                match = re.search(r"C_WECHSEL\((\d+)", line)
                if match:
                    new_tool = int(match.group(1))
                    if new_tool != self.current_tool:
                        tool_changes += 1
                        tool_change_lines.append(f"  Line {i}: C_WECHSEL to T{new_tool}")
                        self.current_tool = new_tool
                        tool_changed = True
            
            # OPUS D-code tool selection
            elif not line.strip().startswith(";"):
                match = re.search(r"^\s*N?\d*\s*D(\d{3,})\b", line)
                if match:
                    new_tool = int(match.group(1))
                    if new_tool > 100 and new_tool != self.current_tool:
                        tool_changes += 1
                        tool_change_lines.append(f"  Line {i}: D-code to D{new_tool}")
                        self.current_tool = new_tool
                        tool_changed = True
            
            # Count spindle starts
            if any(x in line for x in ["CH_SPINDEL.NC", "CP_TSPEED.NC", "C_TSL"]):
                if "@P2=1" in line or "@P2=3" in line or not "@P2=0" in line:
                    spindle_starts += 1
            
            # Count L CYCLE calls (excluding tool/spindle operations)
            if "L CYCLE" in line:
                if not any(x in line for x in ["CH_TOOLCHANGE", "CP_TC", "CH_SPINDEL", "CP_TSPEED"]):
                    cycle_calls += 1
            
            # Process movements and calculate time
            coords = self.parse_coordinates(clean_line)
            
            # G0 - Rapid movement
            if re.search(r'\bG0+\b', clean_line):
                movements['G0'] += 1
                if coords:
                    new_x = coords.get('X', self.current_x)
                    new_y = coords.get('Y', self.current_y)
                    new_z = coords.get('Z', self.current_z)
                    
                    distance = self.calculate_distance(
                        self.current_x, self.current_y, self.current_z,
                        new_x, new_y, new_z
                    )
                    
                    # Time = distance / feedrate (convert to seconds)
                    time_seconds = (distance / self.rapid_feedrate) * 60 if distance > 0 else 0
                    rapid_time += time_seconds
                    
                    self.current_x = new_x
                    self.current_y = new_y
                    self.current_z = new_z
            
            # G1 - Linear cutting
            elif re.search(r'\bG0*1\b', clean_line):
                movements['G1'] += 1
                if coords and self.current_feedrate > 0:
                    new_x = coords.get('X', self.current_x)
                    new_y = coords.get('Y', self.current_y)
                    new_z = coords.get('Z', self.current_z)
                    
                    distance = self.calculate_distance(
                        self.current_x, self.current_y, self.current_z,
                        new_x, new_y, new_z
                    )
                    
                    # Time = distance / feedrate (convert to seconds)
                    time_seconds = (distance / self.current_feedrate) * 60 if distance > 0 else 0
                    cut_time += time_seconds
                    
                    self.current_x = new_x
                    self.current_y = new_y
                    self.current_z = new_z
            
            # G2/G3 - Arc movements (simplified - treat as linear for time estimate)
            elif re.search(r'\bG0*2\b', clean_line):
                movements['G2'] += 1
                if coords and self.current_feedrate > 0:
                    new_x = coords.get('X', self.current_x)
                    new_y = coords.get('Y', self.current_y)
                    new_z = coords.get('Z', self.current_z)
                    
                    # Simplified arc calculation (actual arc length would need I,J,K)
                    distance = self.calculate_distance(
                        self.current_x, self.current_y, self.current_z,
                        new_x, new_y, new_z
                    ) * 1.57  # Approximate arc as 1.57x straight line
                    
                    time_seconds = (distance / self.current_feedrate) * 60 if distance > 0 else 0
                    cut_time += time_seconds
                    
                    self.current_x = new_x
                    self.current_y = new_y
                    self.current_z = new_z
                    
            elif re.search(r'\bG0*3\b', clean_line):
                movements['G3'] += 1
                if coords and self.current_feedrate > 0:
                    new_x = coords.get('X', self.current_x)
                    new_y = coords.get('Y', self.current_y)
                    new_z = coords.get('Z', self.current_z)
                    
                    distance = self.calculate_distance(
                        self.current_x, self.current_y, self.current_z,
                        new_x, new_y, new_z
                    ) * 1.57
                    
                    time_seconds = (distance / self.current_feedrate) * 60 if distance > 0 else 0
                    cut_time += time_seconds
                    
                    self.current_x = new_x
                    self.current_y = new_y
                    self.current_z = new_z
        
        # Calculate overhead times
        tool_change_overhead = tool_changes * self.tool_change_time
        spindle_overhead = spindle_starts * self.spindle_start_time
        cycle_overhead = cycle_calls * self.cycle_overhead
        
        # Total times
        total_overhead = rapid_time + tool_change_overhead + spindle_overhead + cycle_overhead
        total_cycle_time = cut_time + total_overhead
        
        # Convert to minutes for display
        cut_time_min = cut_time / 60
        rapid_time_min = rapid_time / 60
        overhead_time_min = total_overhead / 60
        total_time_min = total_cycle_time / 60
        
        # Display results
        print("\n📊 TIMING ANALYSIS")
        print("-" * 50)
        print(f"TOTAL CYCLE TIME:    {total_time_min:8.2f} minutes")
        print(f"  Cut Time:          {cut_time_min:8.2f} minutes ({cut_time_min/total_time_min*100:.1f}%)")
        print(f"  Overhead Time:     {overhead_time_min:8.2f} minutes ({overhead_time_min/total_time_min*100:.1f}%)")
        
        print("\n📋 OVERHEAD BREAKDOWN")
        print("-" * 50)
        print(f"  Rapid moves:       {rapid_time:8.1f} seconds")
        print(f"  Tool changes:      {tool_change_overhead:8.1f} seconds ({tool_changes} × {self.tool_change_time}s)")
        print(f"  Spindle starts:    {spindle_overhead:8.1f} seconds ({spindle_starts} × {self.spindle_start_time}s)")
        print(f"  Cycle calls:       {cycle_overhead:8.1f} seconds ({cycle_calls} × {self.cycle_overhead}s)")
        print(f"  TOTAL OVERHEAD:    {total_overhead:8.1f} seconds")
        
        print("\n🔧 TOOL CHANGES")
        print("-" * 50)
        if tool_change_lines:
            for line in tool_change_lines:
                print(line)
        print(f"  Total: {tool_changes} tool changes")
        
        print("\n📐 MOVEMENT SUMMARY")
        print("-" * 50)
        print(f"  G0 (Rapid):        {movements['G0']} moves")
        print(f"  G1 (Linear cut):   {movements['G1']} moves")
        print(f"  G2 (Arc CW):       {movements['G2']} moves")
        print(f"  G3 (Arc CCW):      {movements['G3']} moves")
        print(f"  Total cuts:        {movements['G1'] + movements['G2'] + movements['G3']} moves")
        
        print("\n✅ VALIDATION")
        print("-" * 50)
        if tool_changes == 2:
            print(f"  ✓ Tool changes: {tool_changes} (Expected: 2)")
        else:
            print(f"  ✗ Tool changes: {tool_changes} (Expected: 2)")
        
        return {
            'total_time': total_time_min,
            'cut_time': cut_time_min,
            'overhead_time': overhead_time_min,
            'tool_changes': tool_changes
        }

# Run analysis
analyzer = CNCTimingAnalyzer()

files = [
    ("opus.nc", "OPUS postprocessor (RB_OPUS_V7)"),
    ("nesting.NC", "HH7/Nesting postprocessor"),
    ("Field1.spf", "Vision/Siemens postprocessor")
]

print("CNC COMPLETE TIMING ANALYSIS")
print("Analyzing cycle time, cut time, and overhead time")

results = []
for filename, description in files:
    result = analyzer.analyze_file(filename, description)
    results.append((filename, result))

# Summary comparison
print("\n" + "="*70)
print("COMPARISON SUMMARY")
print("="*70)
print(f"{'File':<15} {'Total (min)':<12} {'Cut (min)':<12} {'Overhead (min)':<15} {'Tools':<6}")
print("-" * 70)
for filename, result in results:
    print(f"{filename:<15} {result['total_time']:<12.2f} {result['cut_time']:<12.2f} {result['overhead_time']:<15.2f} {result['tool_changes']:<6}")