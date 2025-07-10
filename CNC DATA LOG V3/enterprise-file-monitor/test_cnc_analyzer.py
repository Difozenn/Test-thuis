#!/usr/bin/env python3
"""
Test script for CNC G-code analyzer using Field1.nc
"""

import json
import os
import sys
from datetime import datetime

# Add the project directory to Python path
sys.path.insert(0, '/home/difusion/Projects/CNC DATA LOG V3/enterprise-file-monitor')

# Mock the C# classes for testing
class CNCAnalysis:
    def __init__(self):
        self.Filename = ""
        self.LineCount = 0
        self.TotalTime = 0.0
        self.CuttingTime = 0.0
        self.RapidTime = 0.0
        self.MachineTime = 0.0
        self.ToolChanges = 0
        self.ProcessesCount = 0
        self.MovementStats = {}
        self.ProcessesUsed = []
        self.AnalyzedAt = datetime.utcnow()
        self.AnalysisSuccessful = False
        self.ErrorMessage = ""

class CNCMovement:
    def __init__(self):
        self.Code = ""
        self.X = 0.0
        self.Y = 0.0
        self.Z = 0.0
        self.Feedrate = 0.0
        self.Distance = 0.0
        self.Time = 0.0

class GCodeAnalyzer:
    def __init__(self):
        self._default_feedrates = {
            "G0": 15000,  # Rapid movement (mm/min)
            "G1": 1000,   # Linear interpolation
            "G2": 800,    # Circular interpolation CW
            "G3": 800     # Circular interpolation CCW
        }
        
        self._tool_change_commands = {"M06", "M6", "T"}
        self._spindle_commands = {"M03", "M3", "M04", "M4", "M05", "M5"}
    
    def analyze_file(self, file_path):
        """Analyze a CNC file and return analysis results"""
        analysis = CNCAnalysis()
        analysis.Filename = os.path.basename(file_path)
        
        try:
            if not os.path.exists(file_path):
                analysis.ErrorMessage = "File not found"
                return analysis
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            analysis.LineCount = len(lines)
            
            movements = []
            current_pos = {"X": 0.0, "Y": 0.0, "Z": 0.0}
            current_feedrate = 1000
            spindle_operations = 0
            
            for line in lines:
                clean_line = self._clean_gcode_line(line)
                if not clean_line:
                    continue
                
                # Parse movement
                movement = self._parse_gcode_line(clean_line, current_pos, current_feedrate)
                if movement:
                    movements.append(movement)
                    current_pos = {"X": movement.X, "Y": movement.Y, "Z": movement.Z}
                    current_feedrate = movement.Feedrate if movement.Feedrate > 0 else current_feedrate
                    
                    # Update movement stats
                    if movement.Code not in analysis.MovementStats:
                        analysis.MovementStats[movement.Code] = 0
                    analysis.MovementStats[movement.Code] += 1
                
                # Check for tool changes
                if self._is_tool_change(clean_line):
                    analysis.ToolChanges += 1
                
                # Check for spindle operations
                if self._is_spindle_operation(clean_line):
                    spindle_operations += 1
                
                # Track processes
                process = self._extract_process(clean_line)
                if process and process not in analysis.ProcessesUsed:
                    analysis.ProcessesUsed.append(process)
            
            analysis.ProcessesCount = len(analysis.ProcessesUsed)
            self._calculate_timings(analysis, movements)
            analysis.AnalysisSuccessful = True
            
        except Exception as e:
            analysis.ErrorMessage = f"Analysis failed: {str(e)}"
        
        return analysis
    
    def _clean_gcode_line(self, line):
        """Remove comments and clean up line"""
        # Remove comments
        comment_index = line.find('(')
        if comment_index >= 0:
            line = line[:comment_index]
        
        comment_index = line.find(';')
        if comment_index >= 0:
            line = line[:comment_index]
        
        return line.strip().upper()
    
    def _parse_gcode_line(self, line, current_pos, current_feedrate):
        """Parse a G-code line for movement"""
        parts = line.split()
        if not parts:
            return None
        
        g_code = parts[0]
        if g_code not in self._default_feedrates:
            return None
        
        movement = CNCMovement()
        movement.Code = g_code
        movement.X = current_pos["X"]
        movement.Y = current_pos["Y"]
        movement.Z = current_pos["Z"]
        movement.Feedrate = current_feedrate
        
        # Parse coordinates and feedrate
        for part in parts[1:]:
            if part.startswith("X"):
                try:
                    movement.X = float(part[1:])
                except ValueError:
                    pass
            elif part.startswith("Y"):
                try:
                    movement.Y = float(part[1:])
                except ValueError:
                    pass
            elif part.startswith("Z"):
                try:
                    movement.Z = float(part[1:])
                except ValueError:
                    pass
            elif part.startswith("F"):
                try:
                    movement.Feedrate = float(part[1:])
                except ValueError:
                    pass
        
        # Calculate distance
        movement.Distance = ((movement.X - current_pos["X"])**2 + 
                           (movement.Y - current_pos["Y"])**2 + 
                           (movement.Z - current_pos["Z"])**2)**0.5
        
        # Calculate time (distance / feedrate) - result in minutes
        feedrate_to_use = movement.Feedrate if movement.Feedrate > 0 else self._default_feedrates[g_code]
        movement.Time = movement.Distance / feedrate_to_use  # minutes
        
        return movement
    
    def _is_tool_change(self, line):
        """Check if line is a tool change command"""
        return any(cmd in line for cmd in self._tool_change_commands)
    
    def _is_spindle_operation(self, line):
        """Check if line is a spindle operation"""
        return any(cmd in line for cmd in self._spindle_commands)
    
    def _extract_process(self, line):
        """Extract process type from line"""
        if line.startswith("G1") or line.startswith("G2") or line.startswith("G3"):
            return "CUTTING"
        elif line.startswith("G0"):
            return "RAPID"
        elif any(cmd in line for cmd in self._tool_change_commands):
            return "TOOL_CHANGE"
        elif line.startswith("M03") or line.startswith("M3") or line.startswith("M04") or line.startswith("M4"):
            return "SPINDLE_START"
        elif line.startswith("M05") or line.startswith("M5"):
            return "SPINDLE_STOP"
        elif line.startswith("M"):
            return "MACHINE_FUNCTION"
        
        return None
    
    def _calculate_timings(self, analysis, movements):
        """Calculate timing statistics"""
        analysis.RapidTime = sum(m.Time for m in movements if m.Code == "G0")
        analysis.CuttingTime = sum(m.Time for m in movements if m.Code in ["G1", "G2", "G3"])
        analysis.TotalTime = sum(m.Time for m in movements)
        
        # Add tool change time (assume 30 seconds per tool change)
        analysis.MachineTime = analysis.TotalTime + (analysis.ToolChanges * 0.5)  # 30 seconds = 0.5 minutes

def test_field1_analysis():
    """Test the CNC analyzer with Field1.nc"""
    print("=" * 60)
    print("Testing CNC Analysis with Field1.nc")
    print("=" * 60)
    
    analyzer = GCodeAnalyzer()
    field1_path = "/home/difusion/Projects/CNC DATA LOG V3/enterprise-file-monitor/Field1.nc"
    
    print(f"Analyzing file: {field1_path}")
    print("-" * 40)
    
    analysis = analyzer.analyze_file(field1_path)
    
    if analysis.AnalysisSuccessful:
        print("✅ Analysis SUCCESSFUL!")
        print(f"📄 File: {analysis.Filename}")
        print(f"📝 Lines: {analysis.LineCount:,}")
        print(f"⏱️  Total Time: {analysis.TotalTime:.2f} minutes")
        print(f"🔥 Cutting Time: {analysis.CuttingTime:.2f} minutes")
        print(f"⚡ Rapid Time: {analysis.RapidTime:.2f} minutes")
        print(f"🏭 Machine Time: {analysis.MachineTime:.2f} minutes")
        print(f"🔧 Tool Changes: {analysis.ToolChanges}")
        print(f"⚙️  Processes: {analysis.ProcessesCount}")
        
        if analysis.MovementStats:
            print("\n📊 Movement Statistics:")
            for code, count in analysis.MovementStats.items():
                print(f"   {code}: {count:,} movements")
        
        if analysis.ProcessesUsed:
            print(f"\n🔄 Processes Used: {', '.join(analysis.ProcessesUsed)}")
        
        print(f"\n🕐 Analyzed at: {analysis.AnalyzedAt}")
        
        # Calculate efficiency metrics
        if analysis.MachineTime > 0:
            cutting_efficiency = (analysis.CuttingTime / analysis.MachineTime) * 100
            rapid_efficiency = (analysis.RapidTime / analysis.MachineTime) * 100
            setup_efficiency = ((analysis.MachineTime - analysis.TotalTime) / analysis.MachineTime) * 100
            
            print(f"\n📈 Efficiency Metrics:")
            print(f"   Cutting Efficiency: {cutting_efficiency:.1f}%")
            print(f"   Rapid Movement: {rapid_efficiency:.1f}%")
            print(f"   Setup/Tool Changes: {setup_efficiency:.1f}%")
        
        # Production estimates
        print(f"\n🏭 Production Estimates:")
        print(f"   Parts per hour: {60 / analysis.MachineTime:.1f} parts/hour")
        print(f"   Parts per 8-hour shift: {(8 * 60) / analysis.MachineTime:.1f} parts/shift")
        
    else:
        print("❌ Analysis FAILED!")
        print(f"Error: {analysis.ErrorMessage}")
    
    print("=" * 60)
    
    return analysis

if __name__ == "__main__":
    test_field1_analysis()