import re
import math
import sys

class CNCCycleTimeCalculator:
    def __init__(self, rapid_speed=20000, tool_change_time=20):
        self.rapid_speed = rapid_speed  # mm/min
        self.tool_change_time = tool_change_time  # seconds
        self.current_pos = {'X': 0, 'Y': 0, 'Z': 0}
        self.current_feed = 0
        self.debug = False  # Enable debugging
        
    def parse_nc_file(self, filename):
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        results = {
            'tool_changes': 0,
            'cutting_time': 0,
            'rapid_time': 0,
            'total_time': 0,
            'processes': [],
            'line_count': len(lines),
            'g0_moves': 0,
            'g1_moves': 0,
            'g2_moves': 0,
            'g3_moves': 0
        }
        
        current_process = None
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Check for process markers in comments
            if line.startswith(';'):
                if 'Process #' in line:
                    match = re.search(r'Process #(\d+)', line)
                    if match:
                        process_num = int(match.group(1))
                        if process_num > 0:
                            if current_process:
                                results['processes'].append(current_process)
                            current_process = {'number': process_num, 'time': 0}
                            if self.debug and process_num == 1:
                                print(f"Found Process #{process_num}")
                continue
                
            # Tool change detection
            if 'CH_TOOLCHANGE.NC' in line:
                results['tool_changes'] += 1
                if self.debug and results['tool_changes'] == 1:
                    print(f"Found tool change at line {line_num}")
                
            # Look for G-code commands anywhere in the line
            # Extract feed rate if present
            feed_match = re.search(r'F(\d+\.?\d*)', line)
            if feed_match:
                self.current_feed = float(feed_match.group(1))
                
            # Look for G0 (rapid move)
            if re.search(r'\bG0\b|\bG00\b', line):
                results['g0_moves'] += 1
                time = self._calculate_move_time_from_line(line, self.rapid_speed)
                results['rapid_time'] += time
                self._update_position_from_line(line)
                
            # Look for G1, G2, G3 (cutting moves)
            elif re.search(r'\bG1\b|\bG01\b|\bG2\b|\bG02\b|\bG3\b|\bG03\b', line):
                if re.search(r'\bG1\b|\bG01\b', line):
                    results['g1_moves'] += 1
                elif re.search(r'\bG2\b|\bG02\b', line):
                    results['g2_moves'] += 1
                    if self.debug and results['g2_moves'] <= 3:
                        print(f"G2 arc at line {line_num}: {line.strip()}")
                elif re.search(r'\bG3\b|\bG03\b', line):
                    results['g3_moves'] += 1
                    
                if self.current_feed > 0:
                    time = self._calculate_move_time_from_line(line, self.current_feed)
                    results['cutting_time'] += time
                    if current_process:
                        current_process['time'] += time
                    # Debug arc moves
                    if self.debug and re.search(r'\bG[0]?[23]\b', line) and results['g2_moves'] + results['g3_moves'] <= 3:
                        print(f"  Arc time: {time*60:.2f} seconds at F{self.current_feed}")
                self._update_position_from_line(line)
        
        # Add last process
        if current_process:
            results['processes'].append(current_process)
        
        # Calculate total time in seconds
        results['total_time'] = (results['tool_changes'] * self.tool_change_time + 
                                results['cutting_time'] * 60 + 
                                results['rapid_time'] * 60)
        
        if self.debug:
            print(f"\nDebug Summary:")
            print(f"Lines processed: {results['line_count']}")
            print(f"G0 moves found: {results['g0_moves']}")
            print(f"G1 moves found: {results['g1_moves']}")
            print(f"G2 moves found: {results['g2_moves']}")
            print(f"G3 moves found: {results['g3_moves']}")
            print(f"Tool changes found: {results['tool_changes']}")
            print(f"Processes found: {len(results['processes'])}")
        
        return results
    
    def _calculate_move_time_from_line(self, line, feed_rate):
        """Calculate time for a move in minutes by parsing the line"""
        new_pos = self.current_pos.copy()
        
        # Extract positions using regex
        x_match = re.search(r'X([-+]?\d*\.?\d+)', line)
        y_match = re.search(r'Y([-+]?\d*\.?\d+)', line)
        z_match = re.search(r'Z([-+]?\d*\.?\d+)', line)
        
        if x_match:
            new_pos['X'] = float(x_match.group(1))
        if y_match:
            new_pos['Y'] = float(y_match.group(1))
        if z_match:
            new_pos['Z'] = float(z_match.group(1))
        
        # Check if this is a G2 or G3 arc move
        if re.search(r'\bG[0]?2\b|\bG[0]?3\b', line):
            # Extract radius for arc calculation
            r_match = re.search(r'R=([-+]?\d*\.?\d+)', line)
            if r_match:
                radius = float(r_match.group(1))
                # Calculate chord length (straight line distance)
                dx = new_pos['X'] - self.current_pos['X']
                dy = new_pos['Y'] - self.current_pos['Y']
                dz = new_pos['Z'] - self.current_pos['Z']
                chord_length = math.sqrt(dx**2 + dy**2 + dz**2)
                
                # For arc moves, calculate the actual arc length
                # For small arcs, use approximation. For full circles, chord_length ≈ 0
                if chord_length < 0.001 and abs(radius) > 0:
                    # Likely a full circle
                    arc_length = 2 * math.pi * abs(radius)
                elif chord_length > 0 and abs(radius) > 0:
                    # Calculate arc length from chord and radius
                    # First check if chord is longer than diameter (invalid)
                    if chord_length > 2 * abs(radius):
                        # Use chord length as approximation
                        arc_length = chord_length
                    else:
                        # Calculate central angle using law of cosines
                        # angle = 2 * arcsin(chord / (2 * radius))
                        central_angle = 2 * math.asin(min(chord_length / (2 * abs(radius)), 1.0))
                        arc_length = abs(radius) * central_angle
                else:
                    arc_length = chord_length
                
                # Add Z component if present (helical interpolation)
                if abs(dz) > 0.001:
                    # For helical moves, calculate the 3D path length
                    arc_length = math.sqrt(arc_length**2 + dz**2)
                
                distance = arc_length
            else:
                # No radius specified, use straight line distance
                distance = math.sqrt(
                    (new_pos['X'] - self.current_pos['X'])**2 +
                    (new_pos['Y'] - self.current_pos['Y'])**2 +
                    (new_pos['Z'] - self.current_pos['Z'])**2
                )
        else:
            # Linear move (G0 or G1)
            distance = math.sqrt(
                (new_pos['X'] - self.current_pos['X'])**2 +
                (new_pos['Y'] - self.current_pos['Y'])**2 +
                (new_pos['Z'] - self.current_pos['Z'])**2
            )
        
        # Return time in minutes
        if feed_rate > 0:
            return distance / feed_rate
        return 0
    
    def _update_position_from_line(self, line):
        """Update current position by parsing the line"""
        x_match = re.search(r'X([-+]?\d*\.?\d+)', line)
        y_match = re.search(r'Y([-+]?\d*\.?\d+)', line)
        z_match = re.search(r'Z([-+]?\d*\.?\d+)', line)
        
        if x_match:
            self.current_pos['X'] = float(x_match.group(1))
        if y_match:
            self.current_pos['Y'] = float(y_match.group(1))
        if z_match:
            self.current_pos['Z'] = float(z_match.group(1))

# Usage
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python postprocessor.py <nc_file_path>")
        print("Example: python postprocessor.py Field1.nc")
        sys.exit(1)
    
    nc_file_path = sys.argv[1]
    
    calculator = CNCCycleTimeCalculator(rapid_speed=20000, tool_change_time=20)
    
    try:
        results = calculator.parse_nc_file(nc_file_path)
        
        print(f"\nAnalyzing: {nc_file_path}")
        print("-" * 50)
        print(f"Tool changes: {results['tool_changes']}")
        print(f"Tool change time: {results['tool_changes'] * calculator.tool_change_time:.1f} seconds")
        print(f"Cutting time: {results['cutting_time']*60:.1f} seconds ({results['cutting_time']:.1f} minutes)")
        print(f"  - G1 moves: {results['g1_moves']}")
        print(f"  - G2 moves: {results['g2_moves']}")  
        print(f"  - G3 moves: {results['g3_moves']}")
        print(f"Rapid time: {results['rapid_time']*60:.1f} seconds ({results['rapid_time']:.1f} minutes)")
        print("-" * 50)
        print(f"Total cycle time: {results['total_time']:.1f} seconds ({results['total_time']/60:.1f} minutes)")
        
        if results['processes']:
            print(f"\nFound {len(results['processes'])} processes")
            # Show first 5 processes as example
            for i, process in enumerate(results['processes'][:5]):
                print(f"Process {process['number']}: {process['time']*60:.1f} seconds")
            if len(results['processes']) > 5:
                print(f"... and {len(results['processes']) - 5} more processes")
                
    except FileNotFoundError:
        print(f"Error: File '{nc_file_path}' not found!")
    except Exception as e:
        print(f"Error processing file: {e}")
        import traceback
        traceback.print_exc()