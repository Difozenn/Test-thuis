#!/usr/bin/env python3
"""
Accurate TCALC-style timing analysis matching the expected output
"""

import re
import math

class TCALCAnalyzer:
    def __init__(self):
        # TCALC machine configuration (HH7 defaults)
        self.rapid_feedrate = 60000  # mm/min (60m/min for modern CNCs)
        self.tool_change_time = 13.05  # seconds per tool change (26.1s / 2 = 13.05s)
        self.default_cutting_feed = 10000  # mm/min default for cutting
        
        # Position tracking
        self.current_x = 0
        self.current_y = 0
        self.current_z = 0
        self.current_feedrate = 0
        self.current_tool = 0
        
        # Tool tracking for per-tool timing
        self.tool_times = {}
        self.tool_distances = {}
        
    def calculate_distance(self, x1, y1, z1, x2, y2, z2):
        """Calculate 3D distance between two points"""
        return math.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)
    
    def parse_coordinates(self, line):
        """Extract X, Y, Z coordinates from a line"""
        coords = {}
        
        # Handle both formats: X123.45 and X=123.45
        x_match = re.search(r'X[=]?([-+]?\d*\.?\d+)', line)
        y_match = re.search(r'Y[=]?([-+]?\d*\.?\d+)', line)
        z_match = re.search(r'Z[=]?([-+]?\d*\.?\d+)', line)
        
        if x_match:
            coords['X'] = float(x_match.group(1))
        if y_match:
            coords['Y'] = float(y_match.group(1))
        if z_match:
            coords['Z'] = float(z_match.group(1))
            
        return coords
    
    def analyze_nesting_file(self, filename):
        """Analyze nesting.NC file specifically to match TCALC output"""
        
        print(f"\n{'='*70}")
        print(f"TCALC-STYLE ANALYSIS: {filename}")
        print(f"Format: HH7 V7.5.5.93")
        print(f"{'='*70}")
        
        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except:
            with open(filename, 'r', encoding='latin-1') as f:
                lines = f.readlines()
        
        # Timing accumulators
        rapid_time = 0  # G0 movements
        process_time = 0  # G1, G2, G3 movements (cutting)
        tool_changes = 0
        total_process_distance = 0  # Total cutting distance in mm
        
        # Per-tool tracking
        current_tool_start_time = 0
        current_tool_distance = 0
        tool_info = {}
        
        # Reset position
        self.current_x = 0
        self.current_y = 0
        self.current_z = 0
        self.current_feedrate = self.default_cutting_feed
        self.current_tool = 0
        
        for i, line in enumerate(lines, 1):
            clean_line = line.split(';')[0].strip()
            if not clean_line:
                continue
            
            # Extract feedrate (F-codes)
            f_match = re.search(r'F([-+]?\d*\.?\d+)', clean_line)
            if f_match:
                self.current_feedrate = float(f_match.group(1))
            
            # Check for tool changes
            tool_changed = False
            
            # HH7/Nesting format: CP_TC.NC
            if "CP_TC.NC" in line:
                match = re.search(r"@P4=(\d+)", line)
                if match:
                    new_tool = int(match.group(1))
                    if new_tool != self.current_tool:
                        # Save previous tool timing
                        if self.current_tool > 0 and self.current_tool in tool_info:
                            tool_info[self.current_tool]['time'] = process_time - current_tool_start_time
                            tool_info[self.current_tool]['distance'] = current_tool_distance
                        
                        tool_changes += 1
                        self.current_tool = new_tool
                        current_tool_start_time = process_time
                        current_tool_distance = 0
                        
                        # Get tool name from comments
                        tool_name = f"Tool {new_tool}"
                        if i > 1:
                            # Look for tool description in nearby lines
                            for j in range(max(0, i-10), min(len(lines), i+5)):
                                if f"Box:  {new_tool}" in lines[j] or f"ID:{new_tool}" in lines[j]:
                                    # Extract tool description
                                    desc_match = re.search(r'([VSF]F \d+ R[^;]*)', lines[j])
                                    if desc_match:
                                        tool_name = f"({new_tool}) {desc_match.group(1).strip()}"
                                    break
                        
                        if new_tool not in tool_info:
                            tool_info[new_tool] = {'name': tool_name, 'time': 0, 'distance': 0}
            
            # Process movements
            coords = self.parse_coordinates(clean_line)
            
            # G0 - Rapid movement
            if re.search(r'\bG0+\b', clean_line):
                if coords:
                    new_x = coords.get('X', self.current_x)
                    new_y = coords.get('Y', self.current_y)
                    new_z = coords.get('Z', self.current_z)
                    
                    distance = self.calculate_distance(
                        self.current_x, self.current_y, self.current_z,
                        new_x, new_y, new_z
                    )
                    
                    # Rapid time calculation
                    if distance > 0:
                        time_seconds = (distance / self.rapid_feedrate) * 60
                        rapid_time += time_seconds
                    
                    self.current_x = new_x
                    self.current_y = new_y
                    self.current_z = new_z
            
            # G1 - Linear cutting
            elif re.search(r'\bG0*1\b', clean_line):
                if coords:
                    new_x = coords.get('X', self.current_x)
                    new_y = coords.get('Y', self.current_y)
                    new_z = coords.get('Z', self.current_z)
                    
                    distance = self.calculate_distance(
                        self.current_x, self.current_y, self.current_z,
                        new_x, new_y, new_z
                    )
                    
                    if distance > 0 and self.current_feedrate > 0:
                        # Process time calculation
                        time_seconds = (distance / self.current_feedrate) * 60
                        process_time += time_seconds
                        total_process_distance += distance
                        current_tool_distance += distance
                    
                    self.current_x = new_x
                    self.current_y = new_y
                    self.current_z = new_z
            
            # G2/G3 - Arc movements
            elif re.search(r'\bG0*[23]\b', clean_line):
                if coords:
                    new_x = coords.get('X', self.current_x)
                    new_y = coords.get('Y', self.current_y)
                    new_z = coords.get('Z', self.current_z)
                    
                    # Get arc center (I, J values)
                    i_match = re.search(r'I([-+]?\d*\.?\d+)', clean_line)
                    j_match = re.search(r'J([-+]?\d*\.?\d+)', clean_line)
                    
                    if i_match and j_match:
                        # Calculate actual arc length
                        i_val = float(i_match.group(1))
                        j_val = float(j_match.group(1))
                        
                        # Center of arc
                        cx = self.current_x + i_val
                        cy = self.current_y + j_val
                        
                        # Radius
                        r = math.sqrt(i_val**2 + j_val**2)
                        
                        # Start and end angles
                        start_angle = math.atan2(self.current_y - cy, self.current_x - cx)
                        end_angle = math.atan2(new_y - cy, new_x - cx)
                        
                        # Arc angle
                        arc_angle = abs(end_angle - start_angle)
                        if arc_angle > math.pi:
                            arc_angle = 2 * math.pi - arc_angle
                        
                        # Arc length
                        distance = r * arc_angle
                    else:
                        # Fallback: approximate as 1.5x straight line
                        distance = self.calculate_distance(
                            self.current_x, self.current_y, self.current_z,
                            new_x, new_y, new_z
                        ) * 1.5
                    
                    if distance > 0 and self.current_feedrate > 0:
                        time_seconds = (distance / self.current_feedrate) * 60
                        process_time += time_seconds
                        total_process_distance += distance
                        current_tool_distance += distance
                    
                    self.current_x = new_x
                    self.current_y = new_y
                    self.current_z = new_z
        
        # Save last tool timing
        if self.current_tool > 0 and self.current_tool in tool_info:
            tool_info[self.current_tool]['time'] = process_time - current_tool_start_time
            tool_info[self.current_tool]['distance'] = current_tool_distance
        
        # Calculate total times
        tool_change_time = tool_changes * self.tool_change_time
        total_time = process_time + rapid_time + tool_change_time
        
        # Display TCALC-style output
        print("\nSumme Bearbeitungszeiten/machining time")
        print("* annähernde Berechnung, alle Angaben ohne Gewähr")
        print("* expected times, no guarantee for this calculation")
        print("\n")
        print("Beschreibung/Description:                    Dauer/time")
        print("-" * 60)
        
        # Format time as minutes and seconds
        def format_time(seconds):
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes} Min {secs:.1f} Sek"
        
        print(f" Gesamtzeit:                                  {format_time(total_time)}")
        print("(total time)\n")
        
        print(f"Summe Bearbeitungszeiten:                    {format_time(process_time)}")
        print("(total processing time)\n")
        
        print(f"Summe Werkzeugwechselzeiten:                 {format_time(tool_change_time)}")
        print("(total toolchange)\n")
        
        print(f"Summe Eilgänge:                              {format_time(rapid_time)}")
        print("(total G0)\n")
        
        # Format distance
        meters = int(total_process_distance // 1000)
        mm = int(total_process_distance % 1000)
        print(f"Summe Prozesswege:                           {meters} m {mm} mm")
        print("(total G1/G2 process)\n\n\n")
        
        print("Einsatzzeiten nach Werkzeug")
        print("(tool processing time)")
        print(" Werkzeug/Tool:                                Zeit/Time               Processdistance")
        print("-" * 80)
        
        # Display per-tool information
        for tool_id, info in sorted(tool_info.items()):
            tool_name = info['name']
            tool_time = info['time']
            tool_dist = info['distance']
            
            # Format distance
            t_meters = int(tool_dist // 1000)
            t_mm = int(tool_dist % 1000)
            
            print(f"\n {tool_name:<40} {format_time(tool_time):<20} {t_meters} m {t_mm} mm")
        
        return {
            'total_time': total_time,
            'process_time': process_time,
            'tool_change_time': tool_change_time,
            'rapid_time': rapid_time,
            'total_distance': total_process_distance,
            'tool_changes': tool_changes
        }

# Run analysis
analyzer = TCALCAnalyzer()

# Analyze nesting.NC which should match the TCALC output shown
result = analyzer.analyze_nesting_file("nesting.NC")

print("\n" + "="*70)
print("VALIDATION")
print("="*70)
print(f"Expected total time: ~39.5 seconds")
print(f"Calculated total time: {result['total_time']:.1f} seconds")
print(f"\nExpected processing time: ~10.3 seconds")
print(f"Calculated processing time: {result['process_time']:.1f} seconds")
print(f"\nExpected tool changes: 2")
print(f"Calculated tool changes: {result['tool_changes']}")