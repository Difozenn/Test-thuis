#!/usr/bin/env python3
"""
Debug script to understand why timing doesn't match TCALC
"""

import re
import os

def analyze_movements(filepath):
    """Count and categorize all movements in the file"""
    
    print(f"\nAnalyzing movements in: {filepath}")
    print("=" * 60)
    
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    # Movement counters
    g0_count = 0
    g1_count = 0
    g2_count = 0
    g3_count = 0
    tool_changes = 0
    
    # Distance accumulators (rough estimate)
    g0_distance = 0
    g1_distance = 0
    
    # Current position
    current_x = 0
    current_y = 0
    current_z = 0
    
    for i, line in enumerate(lines, 1):
        # Remove comments
        if ';' in line:
            line = line[:line.index(';')]
        line = line.strip().upper()
        
        if not line:
            continue
        
        # Count tool changes
        if 'CH_TOOLCHANGE' in line or 'CP_TC.NC' in line or 'C_WECHSEL' in line:
            tool_changes += 1
            print(f"Line {i}: Tool change detected")
        
        # Count movements
        if re.search(r'\bG0\d?\b', line):
            g0_count += 1
            # Try to extract positions
            x_match = re.search(r'X[=]?([-\d.]+)', line)
            y_match = re.search(r'Y[=]?([-\d.]+)', line)
            z_match = re.search(r'Z[=]?([-\d.]+)', line)
            
            if x_match or y_match or z_match:
                new_x = float(x_match.group(1)) if x_match else current_x
                new_y = float(y_match.group(1)) if y_match else current_y
                new_z = float(z_match.group(1)) if z_match else current_z
                
                dist = ((new_x - current_x)**2 + (new_y - current_y)**2 + (new_z - current_z)**2)**0.5
                g0_distance += dist
                
                if dist > 0.1:  # Only show significant moves
                    print(f"Line {i}: G0 move {dist:.1f}mm from ({current_x:.1f},{current_y:.1f},{current_z:.1f}) to ({new_x:.1f},{new_y:.1f},{new_z:.1f})")
                
                current_x, current_y, current_z = new_x, new_y, new_z
        
        elif re.search(r'\bG0?1\b', line):
            g1_count += 1
            # Extract feedrate if present
            f_match = re.search(r'F([\d.]+)', line)
            if f_match:
                feedrate = float(f_match.group(1))
                if feedrate > 0:
                    # Try to extract positions
                    x_match = re.search(r'X[=]?([-\d.]+)', line)
                    y_match = re.search(r'Y[=]?([-\d.]+)', line)
                    z_match = re.search(r'Z[=]?([-\d.]+)', line)
                    
                    if x_match or y_match or z_match:
                        new_x = float(x_match.group(1)) if x_match else current_x
                        new_y = float(y_match.group(1)) if y_match else current_y
                        new_z = float(z_match.group(1)) if z_match else current_z
                        
                        dist = ((new_x - current_x)**2 + (new_y - current_y)**2 + (new_z - current_z)**2)**0.5
                        g1_distance += dist
                        
                        if dist > 0.1:  # Only show significant moves
                            time = (dist / feedrate) * 60  # seconds
                            print(f"Line {i}: G1 move {dist:.1f}mm @ F{feedrate} = {time:.2f}s")
                        
                        current_x, current_y, current_z = new_x, new_y, new_z
        
        elif re.search(r'\bG0?2\b', line):
            g2_count += 1
            f_match = re.search(r'F([\d.]+)', line)
            r_match = re.search(r'R[=]?([\d.]+)|CR[=]?([\d.]+)', line)
            if f_match and r_match:
                feedrate = float(f_match.group(1))
                radius = float(r_match.group(1) if r_match.group(1) else r_match.group(2))
                # Approximate arc as 1/4 circle
                arc_length = radius * 3.14159 / 2
                time = (arc_length / feedrate) * 60
                print(f"Line {i}: G2 arc R{radius:.1f} @ F{feedrate} ≈ {time:.2f}s")
        
        elif re.search(r'\bG0?3\b', line):
            g3_count += 1
            f_match = re.search(r'F([\d.]+)', line)
            r_match = re.search(r'R[=]?([\d.]+)|CR[=]?([\d.]+)', line)
            if f_match and r_match:
                feedrate = float(f_match.group(1))
                radius = float(r_match.group(1) if r_match.group(1) else r_match.group(2))
                # Approximate arc as 1/4 circle
                arc_length = radius * 3.14159 / 2
                time = (arc_length / feedrate) * 60
                print(f"Line {i}: G3 arc R{radius:.1f} @ F{feedrate} ≈ {time:.2f}s")
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"  Tool changes: {tool_changes}")
    print(f"  G0 rapids: {g0_count} moves, ~{g0_distance:.0f}mm total")
    print(f"  G1 linear: {g1_count} moves, ~{g1_distance:.0f}mm total")
    print(f"  G2 CW arcs: {g2_count} moves")
    print(f"  G3 CCW arcs: {g3_count} moves")
    print()
    
    # Estimate times
    print("TIME ESTIMATES:")
    print(f"  Tool changes: {tool_changes * 13.05:.1f}s (@ 13.05s each)")
    
    # Estimate rapid time (50000 mm/min from PP.ini)
    rapid_time = (g0_distance / 50000) * 60 if g0_distance > 0 else 0
    print(f"  Rapids: {rapid_time:.1f}s (@ 50000 mm/min)")
    
    # Estimate cutting time (average 8000 mm/min)
    cutting_time = (g1_distance / 8000) * 60 if g1_distance > 0 else 0
    print(f"  Cutting: {cutting_time:.1f}s (@ 8000 mm/min avg)")
    
    total = tool_changes * 13.05 + rapid_time + cutting_time
    print(f"  TOTAL: {total:.1f}s")
    
    print(f"\n  Expected TCALC: 39.5s")
    print(f"  Difference: {39.5 - total:.1f}s")

# Analyze all three files
files = ['opus.nc', 'nesting.NC', 'Field1.spf']

for filepath in files:
    analyze_movements(filepath)