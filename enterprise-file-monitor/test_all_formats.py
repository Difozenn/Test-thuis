#!/usr/bin/env python3
"""
Complete test of CNC analysis for all three postprocessor formats
Simulating what FileMonitorTrayApp.cs would do
"""

import re
import math
import os

class CNCFileAnalyzer:
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset analyzer state for new file"""
        self.rapid_feedrate = 60000  # Default
        self.tool_change_time = 13.05  # Default
        self.current_tool = 0
        self.tool_changes = []
        self.movements = {'G0': 0, 'G1': 0, 'G2': 0, 'G3': 0}
        self.current_feedrate = 10000
        self.postprocessor_type = "Unknown"
        
    def extract_config(self, lines):
        """Extract configuration from file header"""
        for line in lines[:100]:  # Check first 100 lines
            # Detect postprocessor type
            if "Post:" in line or "POST:" in line:
                if "OPUS" in line:
                    self.postprocessor_type = "OPUS"
                    print(f"  ✓ Detected OPUS postprocessor: {line.strip()}")
                elif "HH7" in line or "7532DR" in line:
                    self.postprocessor_type = "HH7"
                    print(f"  ✓ Detected HH7 postprocessor: {line.strip()}")
                elif "VISION" in line or "ARTIS" in line:
                    self.postprocessor_type = "Vision/Siemens"
                    print(f"  ✓ Detected Vision/Siemens postprocessor: {line.strip()}")
            
            # Extract spindle speed to estimate rapids
            if "MaxRotSpeed S" in line or "@P7=" in line:
                match = re.search(r"S(\d+)|@P7=(\d+)", line)
                if match:
                    speed = int(match.group(1) or match.group(2))
                    if speed > 10000:
                        self.rapid_feedrate = min(speed * 2.5, 60000)
                        print(f"  ✓ Extracted spindle speed: {speed} → Rapid: {self.rapid_feedrate}mm/min")
    
    def detect_tool_changes(self, lines):
        """Detect tool changes based on postprocessor format"""
        for i, line in enumerate(lines, 1):
            tool_changed = False
            tool_num = 0
            change_type = ""
            
            # 1. OPUS format: CH_TOOLCHANGE.NC
            if "CH_TOOLCHANGE.NC" in line:
                match = re.search(r"@P4=(\d+)", line)
                if match:
                    tool_num = int(match.group(1))
                    change_type = "CH_TOOLCHANGE"
                    tool_changed = True
            
            # 2. HH7 format: CP_TC.NC
            elif "CP_TC.NC" in line:
                match = re.search(r"@P4=(\d+)", line)
                if match:
                    tool_num = int(match.group(1))
                    change_type = "CP_TC"
                    tool_changed = True
            
            # 3. Vision format: C_WECHSEL
            elif "C_WECHSEL" in line:
                match = re.search(r"C_WECHSEL\((\d+)", line)
                if match:
                    tool_num = int(match.group(1))
                    change_type = "C_WECHSEL"
                    tool_changed = True
            
            # 4. OPUS D-codes (after positioning)
            elif not line.strip().startswith(";"):
                clean = line.split(';')[0]
                match = re.search(r"^\s*N?\d*\s*D(\d{3,})\b", clean)
                if match:
                    tool_num = int(match.group(1))
                    if tool_num > 100 and tool_num != self.current_tool:
                        # Check context
                        if i > 1 and "ViewChange" in lines[i-2]:
                            change_type = "D-code"
                            tool_changed = True
            
            if tool_changed and tool_num != self.current_tool:
                self.tool_changes.append({
                    'line': i,
                    'tool': tool_num,
                    'type': change_type,
                    'code': line.strip()[:80]
                })
                self.current_tool = tool_num
    
    def count_movements(self, lines):
        """Count movement commands"""
        for line in lines:
            clean = line.split(';')[0].strip()
            if not clean:
                continue
            
            # Extract feedrate
            f_match = re.search(r'F(\d+\.?\d*)', clean)
            if f_match:
                self.current_feedrate = float(f_match.group(1))
            
            # Count movements
            if re.search(r'\bG0+\b', clean):
                self.movements['G0'] += 1
            elif re.search(r'\bG0*1\b', clean):
                self.movements['G1'] += 1
            elif re.search(r'\bG0*2\b', clean):
                self.movements['G2'] += 1
            elif re.search(r'\bG0*3\b', clean):
                self.movements['G3'] += 1
    
    def calculate_times(self):
        """Calculate estimated times"""
        # Rough estimates based on movement counts
        rapid_time = self.movements['G0'] * (10 / self.rapid_feedrate) * 60  # 10mm avg move
        cut_time = (self.movements['G1'] * 50 + 
                   self.movements['G2'] * 30 + 
                   self.movements['G3'] * 30) / self.current_feedrate * 60
        tool_change_time = len(self.tool_changes) * self.tool_change_time
        
        total_time = rapid_time + cut_time + tool_change_time
        
        return {
            'total': total_time,
            'cutting': cut_time,
            'rapid': rapid_time,
            'tool_change': tool_change_time
        }
    
    def analyze_file(self, filename):
        """Complete analysis of a CNC file"""
        self.reset()
        
        print(f"\n{'='*80}")
        print(f"ANALYZING: {filename}")
        print(f"{'='*80}")
        
        if not os.path.exists(filename):
            print(f"ERROR: File not found!")
            return
        
        # Read file
        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except:
            with open(filename, 'r', encoding='latin-1') as f:
                lines = f.readlines()
        
        print(f"\n📄 FILE INFO:")
        print(f"  Lines: {len(lines)}")
        print(f"  Size: {os.path.getsize(filename)} bytes")
        
        # Extract configuration
        print(f"\n🔧 CONFIGURATION EXTRACTION:")
        self.extract_config(lines)
        
        # Detect tool changes
        print(f"\n🔄 TOOL CHANGES:")
        self.detect_tool_changes(lines)
        
        if self.tool_changes:
            for tc in self.tool_changes:
                print(f"  Line {tc['line']:4d}: {tc['type']:15s} → T{tc['tool']}")
                print(f"           {tc['code']}")
        else:
            print("  No tool changes detected")
        
        print(f"\n  Total tool changes: {len(self.tool_changes)}")
        
        # Count movements
        print(f"\n📐 MOVEMENTS:")
        self.count_movements(lines)
        
        total_cuts = self.movements['G1'] + self.movements['G2'] + self.movements['G3']
        print(f"  G0 (Rapids):     {self.movements['G0']:4d} moves")
        print(f"  G1 (Linear):     {self.movements['G1']:4d} moves")
        print(f"  G2 (Arc CW):     {self.movements['G2']:4d} moves")
        print(f"  G3 (Arc CCW):    {self.movements['G3']:4d} moves")
        print(f"  Total cuts:      {total_cuts:4d} moves")
        
        # Calculate times
        print(f"\n⏱️  TIMING ANALYSIS:")
        times = self.calculate_times()
        
        print(f"  Total cycle time:    {times['total']:7.1f} seconds ({times['total']/60:.2f} min)")
        print(f"  Cutting time:        {times['cutting']:7.1f} seconds ({times['cutting']/60:.2f} min)")
        print(f"  Tool change time:    {times['tool_change']:7.1f} seconds ({len(self.tool_changes)} × {self.tool_change_time}s)")
        print(f"  Rapid time:          {times['rapid']:7.1f} seconds")
        
        # Calculate percentages
        if times['total'] > 0:
            cut_pct = (times['cutting'] / times['total']) * 100
            overhead_pct = 100 - cut_pct
            print(f"\n  Cutting:   {cut_pct:5.1f}%")
            print(f"  Overhead:  {overhead_pct:5.1f}%")
        
        # Validation
        print(f"\n✅ VALIDATION:")
        if len(self.tool_changes) == 2:
            print(f"  ✓ Tool changes: {len(self.tool_changes)} (Expected: 2)")
        else:
            print(f"  ✗ Tool changes: {len(self.tool_changes)} (Expected: 2)")
        
        if self.postprocessor_type != "Unknown":
            print(f"  ✓ Postprocessor: {self.postprocessor_type}")
        else:
            print(f"  ⚠ Postprocessor: Not detected")
        
        return {
            'file': filename,
            'postprocessor': self.postprocessor_type,
            'tool_changes': len(self.tool_changes),
            'movements': total_cuts,
            'times': times
        }

# Run tests
print("╔" + "═"*78 + "╗")
print("║" + " CNC ANALYSIS TEST SUITE - ALL POSTPROCESSOR FORMATS".center(78) + "║")
print("║" + " Testing tool change detection and timing calculation".center(78) + "║")
print("╚" + "═"*78 + "╝")

analyzer = CNCFileAnalyzer()
results = []

files = [
    "opus.nc",
    "nesting.NC",
    "Field1.spf"
]

for filename in files:
    result = analyzer.analyze_file(filename)
    if result:
        results.append(result)

# Summary comparison
print(f"\n{'='*80}")
print("SUMMARY COMPARISON")
print(f"{'='*80}")
print(f"{'File':<15} {'Postprocessor':<20} {'Tools':<8} {'Cuts':<8} {'Total(s)':<10} {'Cut(%)':<8}")
print("-" * 80)

for r in results:
    cut_pct = (r['times']['cutting'] / r['times']['total'] * 100) if r['times']['total'] > 0 else 0
    print(f"{r['file']:<15} {r['postprocessor']:<20} {r['tool_changes']:<8} {r['movements']:<8} "
          f"{r['times']['total']:<10.1f} {cut_pct:<8.1f}")

print(f"\n{'='*80}")
print("TEST COMPLETE - All files should show 2 tool changes")
print(f"{'='*80}")