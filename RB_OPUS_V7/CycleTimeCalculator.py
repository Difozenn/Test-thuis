#!/usr/bin/env python3
"""
CNC Cycle Time Calculator for RB_OPUS_V7 Postprocessor
Reads Field1.nc and calculates estimated cycle time based on postprocessor parameters
"""

import re
import math
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class MachineConfig:
    """Machine configuration from PP.ini"""
    rapid_feedrate: float = 50000.0  # DHFeedrateG00 (mm/min)
    tool_change_time: float = 15.0   # Estimated tool change time (seconds)
    spindle_start_time: float = 3.0  # Spindle start/stop time (seconds)
    pin_change_time: float = 2.0     # DHPinChangeTime (seconds)
    cycle_overhead_time: float = 1.0 # Time for cycle calls (seconds)

@dataclass
class Position:
    """3D position coordinates"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    
    def distance_to(self, other: 'Position') -> float:
        """Calculate 3D distance to another position"""
        return math.sqrt(
            (self.x - other.x)**2 + 
            (self.y - other.y)**2 + 
            (self.z - other.z)**2
        )

@dataclass
class Move:
    """Represents a single machine move"""
    move_type: str  # G0, G1, G2, G3
    start_pos: Position
    end_pos: Position
    feedrate: Optional[float]
    distance: float
    estimated_time: float

class CycleTimeCalculator:
    """Main cycle time calculator class"""
    
    def __init__(self, nc_file_path: str, config: Optional[MachineConfig] = None):
        self.nc_file_path = nc_file_path
        self.config = config or MachineConfig()
        self.current_pos = Position()
        self.moves: List[Move] = []
        self.tool_changes = 0
        self.spindle_starts = 0
        self.cycle_calls = 0
        self.total_distance = 0.0
        self.total_cutting_distance = 0.0
        self.total_rapid_distance = 0.0
        
        # Parse patterns from Field1.nc format
        self.patterns = {
            'gcode_line': re.compile(r'^N\d+\s+(.+)$'),
            'move': re.compile(r'(G[0-3])\s*(?:.*?X([-+]?\d*\.?\d+))?(?:.*?Y([-+]?\d*\.?\d+))?(?:.*?Z([-+]?\d*\.?\d+))?(?:.*?F(\d+))?'),
            'arc': re.compile(r'(G[23])\s*.*?R=([-+]?\d*\.?\d+)'),
            'tool_change': re.compile(r'T(\d+)'),
            'spindle': re.compile(r'M[34]|S(\d+)'),
            'cycle_call': re.compile(r'L\s+CYCLE\s*\[NAME=([^]]+)\]'),
            'comment': re.compile(r';\s*---\s*(.+?)\s*---'),
            'coordinates': re.compile(r'[XYZ]([-+]?\d*\.?\d+)'),
        }

    def load_machine_config_from_ini(self, ini_path: str = None) -> None:
        """Load machine configuration from PP.ini file"""
        if ini_path is None:
            ini_path = os.path.join(os.path.dirname(self.nc_file_path), 'PP.ini')
        
        if not os.path.exists(ini_path):
            print(f"Warning: PP.ini not found at {ini_path}, using defaults")
            return
            
        try:
            with open(ini_path, 'r') as f:
                content = f.read()
                
            # Extract machine parameters
            if match := re.search(r'DHFeedrateG00=(\d+)', content):
                self.config.rapid_feedrate = float(match.group(1))
                
            if match := re.search(r'DHPinChangeTime=(\d+)', content):
                self.config.pin_change_time = float(match.group(1))
                
            print(f"Loaded machine config: Rapid={self.config.rapid_feedrate}, PinChange={self.config.pin_change_time}")
                
        except Exception as e:
            print(f"Error loading PP.ini: {e}")

    def parse_nc_file(self) -> None:
        """Parse the NC file and extract all operations"""
        print(f"Parsing NC file: {self.nc_file_path}")
        
        try:
            with open(self.nc_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"Error reading NC file: {e}")
            return

        current_feedrate = None
        line_number = 0
        
        for line in lines:
            line_number += 1
            line = line.strip()
            
            if not line or line.startswith(';'):
                # Skip comments and empty lines, but check for tool info
                if comment_match := self.patterns['comment'].match(line):
                    comment = comment_match.group(1)
                    if 'BOX:' in comment and 'MaxRotSpeed' in comment:
                        self.spindle_starts += 1
                continue
                
            # Extract G-code from line number format
            if gcode_match := self.patterns['gcode_line'].match(line):
                gcode = gcode_match.group(1).strip()
            else:
                gcode = line
                
            # Process the G-code
            self._process_gcode_line(gcode, current_feedrate)
            
            # Update current feedrate if F word is present
            if 'F' in gcode:
                if f_match := re.search(r'F(\d+)', gcode):
                    current_feedrate = float(f_match.group(1))

    def _process_gcode_line(self, gcode: str, current_feedrate: Optional[float]) -> None:
        """Process a single G-code line"""
        
        # Check for cycle calls
        if cycle_match := self.patterns['cycle_call'].search(gcode):
            cycle_name = cycle_match.group(1)
            self.cycle_calls += 1
            
            # Estimate time based on cycle type
            if 'CH_TOOLCHANGE.NC' in cycle_name:
                self.tool_changes += 1
            elif 'START' in cycle_name or 'PROCESSING' in cycle_name:
                pass  # Setup cycles
            
            return
            
        # Check for tool changes
        if self.patterns['tool_change'].search(gcode):
            self.tool_changes += 1
            return
            
        # Check for spindle commands
        if self.patterns['spindle'].search(gcode):
            self.spindle_starts += 1
            return
            
        # Process movement commands
        if move_match := self.patterns['move'].search(gcode):
            self._process_movement(move_match, current_feedrate)

    def _process_movement(self, move_match: re.Match, current_feedrate: Optional[float]) -> None:
        """Process a movement command (G0, G1, G2, G3)"""
        move_type = move_match.group(1)
        
        # Extract coordinates (may be None if not specified)
        x = float(move_match.group(2)) if move_match.group(2) else self.current_pos.x
        y = float(move_match.group(3)) if move_match.group(3) else self.current_pos.y
        z = float(move_match.group(4)) if move_match.group(4) else self.current_pos.z
        feedrate = float(move_match.group(5)) if move_match.group(5) else current_feedrate
        
        # Create new position
        new_pos = Position(x, y, z)
        
        # Calculate distance
        distance = self.current_pos.distance_to(new_pos)
        
        # Determine feedrate for time calculation
        if move_type == 'G0':  # Rapid move
            effective_feedrate = self.config.rapid_feedrate
            self.total_rapid_distance += distance
        else:  # Cutting move (G1, G2, G3)
            effective_feedrate = feedrate or self.config.rapid_feedrate
            self.total_cutting_distance += distance
            
        # Calculate time (feedrate is in mm/min, convert to mm/sec)
        if effective_feedrate > 0:
            time_seconds = (distance / effective_feedrate) * 60.0
        else:
            time_seconds = 0.0
            
        # Create move record
        move = Move(
            move_type=move_type,
            start_pos=self.current_pos,
            end_pos=new_pos,
            feedrate=effective_feedrate,
            distance=distance,
            estimated_time=time_seconds
        )
        
        self.moves.append(move)
        self.total_distance += distance
        
        # Update current position
        self.current_pos = new_pos

    def calculate_cycle_time(self) -> Dict[str, float]:
        """Calculate total estimated cycle time"""
        
        # Calculate movement times by type
        cutting_time = 0.0
        rapid_time = 0.0
        
        for move in self.moves:
            if move.move_type == 'G0':  # Rapid moves
                rapid_time += move.estimated_time
            else:  # Cutting moves (G1, G2, G3)
                cutting_time += move.estimated_time
                
        movement_time = cutting_time + rapid_time
        
        # Calculate overhead times
        tool_change_time = self.tool_changes * self.config.tool_change_time
        spindle_time = self.spindle_starts * self.config.spindle_start_time
        cycle_time = self.cycle_calls * self.config.cycle_overhead_time
        
        # Total cycle time
        total_time = movement_time + tool_change_time + spindle_time + cycle_time
        
        return {
            'movement_time': movement_time,
            'cutting_time': cutting_time,
            'rapid_time': rapid_time,
            'tool_change_time': tool_change_time,
            'spindle_time': spindle_time,
            'cycle_overhead_time': cycle_time,
            'total_time': total_time,
            'total_distance': self.total_distance,
            'cutting_distance': self.total_cutting_distance,
            'rapid_distance': self.total_rapid_distance,
            'tool_changes': self.tool_changes,
            'spindle_starts': self.spindle_starts,
            'cycle_calls': self.cycle_calls,
            'total_moves': len(self.moves)
        }

    def generate_report(self, output_file: Optional[str] = None) -> str:
        """Generate a detailed cycle time report"""
        
        # Load configuration and parse file
        self.load_machine_config_from_ini()
        self.parse_nc_file()
        
        # Calculate times
        results = self.calculate_cycle_time()
        
        # Format times
        def format_time(seconds: float) -> str:
            if seconds < 60:
                return f"{seconds:.1f} sec"
            elif seconds < 3600:
                minutes = seconds / 60
                return f"{minutes:.1f} min ({seconds:.0f} sec)"
            else:
                hours = seconds / 3600
                minutes = (seconds % 3600) / 60
                return f"{hours:.1f} hr {minutes:.0f} min ({seconds:.0f} sec)"
        
        # Generate report
        report_lines = [
            f"CNC Cycle Time Analysis Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"NC File: {os.path.basename(self.nc_file_path)}",
            f"",
            f"=== CYCLE TIME BREAKDOWN ===",
            f"Movement Time:     {format_time(results['movement_time'])}",
            f"Tool Change Time:  {format_time(results['tool_change_time'])}",
            f"Spindle Time:      {format_time(results['spindle_time'])}",
            f"Cycle Overhead:    {format_time(results['cycle_overhead_time'])}",
            f"",
            f"TOTAL CYCLE TIME:  {format_time(results['total_time'])}",
            f"",
            f"=== OPERATION STATISTICS ===",
            f"Total Distance:    {results['total_distance']:.1f} mm",
            f"Cutting Distance:  {results['cutting_distance']:.1f} mm",
            f"Rapid Distance:    {results['rapid_distance']:.1f} mm",
            f"Total Moves:       {results['total_moves']}",
            f"Tool Changes:      {results['tool_changes']}",
            f"Spindle Starts:    {results['spindle_starts']}",
            f"Cycle Calls:       {results['cycle_calls']}",
            f"",
            f"=== MACHINE CONFIGURATION ===",
            f"Rapid Feedrate:    {self.config.rapid_feedrate:.0f} mm/min",
            f"Tool Change Time:  {self.config.tool_change_time:.1f} sec",
            f"Spindle Start Time: {self.config.spindle_start_time:.1f} sec",
            f"Pin Change Time:   {self.config.pin_change_time:.1f} sec",
            f"",
            f"=== PRODUCTION ESTIMATES ===",
            f"Single Part:       {format_time(results['total_time'])}",
            f"10 Parts:          {format_time(results['total_time'] * 10)}",
            f"100 Parts:         {format_time(results['total_time'] * 100)}",
            f"Parts per Hour:    {3600 / results['total_time']:.1f}",
            f"Parts per Day:     {(3600 * 8) / results['total_time']:.0f} (8 hour shift)",
        ]
        
        report = '\n'.join(report_lines)
        
        # Save to file if specified
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    f.write(report)
                print(f"Report saved to: {output_file}")
            except Exception as e:
                print(f"Error saving report: {e}")
        
        return report

def main():
    """Main function for command line usage"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python CycleTimeCalculator.py <Field1.nc> [output_report.txt]")
        print("Example: python CycleTimeCalculator.py Field1.nc cycle_report.txt")
        return
        
    nc_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(nc_file):
        print(f"Error: NC file '{nc_file}' not found")
        return
    
    # Create calculator and generate report
    calculator = CycleTimeCalculator(nc_file)
    report = calculator.generate_report(output_file)
    
    # Print to console
    print(report)

if __name__ == "__main__":
    main()