#!/usr/bin/env python3
"""
Complete CNC Analysis Test - Mimics FileMonitorTrayApp.cs logic
Shows tool changes and total cycle time for all 3 files
"""

import re
import os
import math

class CNCAnalyzer:
    def __init__(self):
        # Constants from FileMonitorTrayApp.cs
        self.TC_51_51 = 13.05  # Tool change time in seconds
        self.DHFeedrateG00 = 50000  # Rapid feedrate mm/min
        self.DEFAULT_CUTTING_FEEDRATE = 3000  # Default if none specified
        
        # State tracking
        self.current_x = 0
        self.current_y = 0
        self.current_z = 0
        self.current_feedrate = 0
        self.last_valid_feedrate = self.DEFAULT_CUTTING_FEEDRATE
        self.current_active_tool = 0
        self.last_tool_change_line = -100
        
    def analyze_file(self, filepath):
        """Analyze a CNC file using the same logic as FileMonitorTrayApp.cs"""
        
        filename = os.path.basename(filepath)
        print(f"\n{'='*70}")
        print(f"ANALYZING: {filename}")
        print(f"{'='*70}")
        
        with open(filepath, 'r', encoding='latin-1') as f:
            lines = f.readlines()
        
        # Reset state for new file
        self.current_x = 0
        self.current_y = 0
        self.current_z = 0
        self.current_feedrate = 0
        self.last_valid_feedrate = self.DEFAULT_CUTTING_FEEDRATE
        self.current_active_tool = 0
        self.last_tool_change_line = -100
        
        # Tracking
        tool_changes = []
        tools_used = []
        movements = []
        machine_ops = {'spindle_starts': 0, 'cycles': 0}
        
        for line_num, line in enumerate(lines, 1):
            clean_line = line.split(';')[0].strip()
            if not clean_line:
                continue
            
            # Extract tool changes using same logic as C#
            tool_change = self.extract_tool_change(line, line_num)
            if tool_change:
                tool_changes.append(tool_change)
                if tool_change['tool'] not in tools_used:
                    tools_used.append(tool_change['tool'])
            
            # Extract feedrate
            feed_match = re.search(r'F(\d+)', clean_line)
            if feed_match:
                feed = int(feed_match.group(1))
                self.current_feedrate = feed
                if feed > 0:
                    self.last_valid_feedrate = feed
            
            # Process movements
            movement = self.process_movement(clean_line)
            if movement:
                movements.append(movement)
            
            # Count machine operations
            if 'CH_SPINDEL.NC' in line or 'CP_TSPEED.NC' in line or 'C_TSL' in line:
                machine_ops['spindle_starts'] += 1
            if 'L CYCLE' in line:
                machine_ops['cycles'] += 1
        
        # Calculate times
        rapid_time_min = sum([m['time'] for m in movements if m['code'] == 'G0'])
        cutting_time_min = sum([m['time'] for m in movements if m['code'] in ['G1', 'G2', 'G3']])
        
        # Convert to seconds for display
        rapid_time_sec = rapid_time_min * 60
        cutting_time_sec = cutting_time_min * 60
        
        # Overhead times in seconds
        tool_change_time_sec = len(tool_changes) * self.TC_51_51
        spindle_time_sec = machine_ops['spindle_starts'] * 1.0
        cycle_overhead_sec = machine_ops['cycles'] * 0.1
        
        # Total times
        overhead_time_sec = rapid_time_sec + tool_change_time_sec + spindle_time_sec + cycle_overhead_sec
        total_time_sec = cutting_time_sec + overhead_time_sec
        
        # Print results
        print(f"\n📊 TOOL CHANGES: {len(tool_changes)}")
        for tc in tool_changes:
            print(f"  Line {tc['line']:4d}: {tc['type']:20s} → Tool {tc['tool']}")
        
        print(f"\n🔧 TOOLS USED: {tools_used}")
        
        print(f"\n⏱️  TIMING BREAKDOWN:")
        print(f"  Cut Time:        {cutting_time_sec:6.1f}s ({cutting_time_sec/60:5.2f} min)")
        print(f"  Rapid Time:      {rapid_time_sec:6.1f}s ({rapid_time_sec/60:5.2f} min)")
        print(f"  Tool Changes:    {tool_change_time_sec:6.1f}s ({len(tool_changes)} × {self.TC_51_51}s)")
        print(f"  Other Overhead:  {spindle_time_sec + cycle_overhead_sec:6.1f}s")
        print(f"  " + "-"*40)
        print(f"  TOTAL TIME:      {total_time_sec:6.1f}s ({total_time_sec/60:5.2f} min)")
        
        # Calculate efficiency
        if total_time_sec > 0:
            efficiency = (cutting_time_sec / total_time_sec) * 100
            print(f"\n📈 EFFICIENCY: {efficiency:.1f}% (cutting / total)")
        
        return {
            'file': filename,
            'tool_changes': len(tool_changes),
            'tools': tools_used,
            'total_time_sec': total_time_sec,
            'cut_time_sec': cutting_time_sec,
            'overhead_time_sec': overhead_time_sec
        }
    
    def extract_tool_change(self, line, line_num):
        """Extract tool changes using same logic as ExtractToolNumbers in C#"""
        
        # Check if too close to last tool change (within 10 lines)
        is_near_recent = abs(line_num - self.last_tool_change_line) < 10
        
        # 1. OPUS format: CH_TOOLCHANGE.NC
        if 'CH_TOOLCHANGE.NC' in line:
            match = re.search(r'@P4=(\d+)', line)
            if match:
                tool = int(match.group(1))
                if not is_near_recent and self.current_active_tool != tool:
                    self.current_active_tool = tool
                    self.last_tool_change_line = line_num
                    return {'line': line_num, 'type': 'CH_TOOLCHANGE', 'tool': tool}
        
        # 2. HH7 format: CP_TC.NC
        if 'CP_TC.NC' in line:
            match = re.search(r'@P4=(\d+)', line)
            if match:
                tool = int(match.group(1))
                if not is_near_recent and self.current_active_tool != tool:
                    self.current_active_tool = tool
                    self.last_tool_change_line = line_num
                    return {'line': line_num, 'type': 'CP_TC', 'tool': tool}
        
        # 3. Vision/Siemens format: C_WECHSEL
        if 'C_WECHSEL' in line:
            match = re.search(r'C_WECHSEL\((\d+)', line)
            if match:
                tool = int(match.group(1))
                if not is_near_recent and self.current_active_tool != tool:
                    self.current_active_tool = tool
                    self.last_tool_change_line = line_num
                    return {'line': line_num, 'type': 'C_WECHSEL', 'tool': tool}
        
        # Skip D-code detection if near recent tool change
        if is_near_recent:
            return None
        
        # 4. OPUS D-code tool selection (WITH the fix)
        clean_line = line.split(';')[0]
        match = re.search(r'^[^;]*\bD(\d{3,})\b', clean_line)
        if match:
            d_code = int(match.group(1))
            if d_code > 100 and self.current_active_tool != d_code:
                self.current_active_tool = d_code
                self.last_tool_change_line = line_num
                return {'line': line_num, 'type': 'D-code', 'tool': d_code}
        
        return None
    
    def process_movement(self, line):
        """Process movement commands and calculate time"""
        
        # Extract new position
        new_x = self.current_x
        new_y = self.current_y
        new_z = self.current_z
        
        x_match = re.search(r'X([-+]?\d*\.?\d+)', line)
        if x_match:
            new_x = float(x_match.group(1))
        
        y_match = re.search(r'Y([-+]?\d*\.?\d+)', line)
        if y_match:
            new_y = float(y_match.group(1))
        
        z_match = re.search(r'Z([-+]?\d*\.?\d+)', line)
        if z_match:
            new_z = float(z_match.group(1))
        
        # Calculate distance
        distance = math.sqrt(
            (new_x - self.current_x)**2 +
            (new_y - self.current_y)**2 +
            (new_z - self.current_z)**2
        )
        
        # Skip micro movements
        if distance < 0.001:
            return None
        
        movement = None
        
        # G0 - Rapid move
        if re.search(r'\bG0\b|\bG00\b', line):
            feedrate = self.DHFeedrateG00
            time_min = distance / feedrate
            movement = {'code': 'G0', 'distance': distance, 'time': time_min}
        
        # G1 - Linear move
        elif re.search(r'\bG1\b|\bG01\b', line):
            feedrate = self.current_feedrate if self.current_feedrate > 0 else self.last_valid_feedrate
            time_min = distance / feedrate
            movement = {'code': 'G1', 'distance': distance, 'time': time_min}
        
        # G2/G3 - Arc moves (simplified)
        elif re.search(r'\bG[0]?[23]\b', line):
            code = 'G2' if re.search(r'\bG[0]?2\b', line) else 'G3'
            feedrate = self.current_feedrate if self.current_feedrate > 0 else self.last_valid_feedrate
            # Simplified arc calculation - assume arc length ≈ 1.5 × chord length
            arc_length = distance * 1.5
            time_min = arc_length / feedrate
            movement = {'code': code, 'distance': arc_length, 'time': time_min}
        
        # Update position
        self.current_x = new_x
        self.current_y = new_y
        self.current_z = new_z
        
        return movement

# Run the test
analyzer = CNCAnalyzer()
results = []

files = [
    '/mnt/c/Users/Rob_v/Desktop/test-werk-main/enterprise-file-monitor/opus.nc',
    '/mnt/c/Users/Rob_v/Desktop/test-werk-main/enterprise-file-monitor/nesting.NC', 
    '/mnt/c/Users/Rob_v/Desktop/test-werk-main/enterprise-file-monitor/Field1.spf'
]

for filepath in files:
    if os.path.exists(filepath):
        results.append(analyzer.analyze_file(filepath))
    else:
        print(f"File not found: {filepath}")

# Summary
print("\n" + "="*70)
print("FINAL SUMMARY - ALL FILES")
print("="*70)
print(f"{'File':<15} {'Tool Changes':<12} {'Tools':<15} {'Total Time':<12} {'Cut Time':<12} {'Overhead':<12}")
print("-"*70)
for r in results:
    tools_str = ','.join(map(str, r['tools']))
    total_str = f"{r['total_time_sec']:.1f}s"
    cut_str = f"{r['cut_time_sec']:.1f}s"
    overhead_str = f"{r['overhead_time_sec']:.1f}s"
    print(f"{r['file']:<15} {r['tool_changes']:<12} {tools_str:<15} {total_str:<12} {cut_str:<12} {overhead_str:<12}")

print("\n✅ Expected: 2 tool changes per file, ~30-40 seconds total time")