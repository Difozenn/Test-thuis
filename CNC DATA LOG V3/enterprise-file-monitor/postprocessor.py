import re
import math
import sys
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

@dataclass
class MachineConfig:
    """Configuration for machine-specific timing parameters"""
    rapid_speed: float = 20000  # mm/min
    tool_change_time: float = 20  # seconds
    spindle_start_time: float = 2  # seconds
    spindle_stop_time: float = 1.5  # seconds
    tcp_on_time: float = 0.5  # seconds
    tcp_off_time: float = 0.3  # seconds
    contour_start_time: float = 0.5  # seconds
    contour_end_time: float = 0.3  # seconds
    dynamic_setup_time: float = 0.5  # seconds
    flush_wait_time: float = 1.0  # seconds
    coordinate_setup_time: float = 0.2  # seconds
    general_cycle_time: float = 0.1  # seconds for other cycles

@dataclass
class MachineOperations:
    """Counter for various machine operations"""
    tool_changes: int = 0
    spindle_starts: int = 0
    spindle_stops: int = 0
    tcp_on: int = 0
    tcp_off: int = 0
    contour_starts: int = 0
    contour_ends: int = 0
    dynamic_setups: int = 0
    flush_waits: int = 0
    coordinate_setups: int = 0
    other_cycles: int = 0

@dataclass
class MovementStats:
    """Statistics for G-code movements"""
    g0_moves: int = 0
    g1_moves: int = 0
    g2_moves: int = 0
    g3_moves: int = 0
    total_cutting_distance: float = 0
    total_rapid_distance: float = 0
    cutting_time: float = 0  # minutes
    rapid_time: float = 0  # minutes

@dataclass
class ProcessInfo:
    """Information about individual processes"""
    number: int
    cutting_time: float = 0  # minutes
    machine_time: float = 0  # seconds
    moves: int = 0

class EnhancedCNCCycleTimeCalculator:
    def __init__(self, config: Optional[MachineConfig] = None):
        """Initialize calculator with machine configuration"""
        self.config = config or MachineConfig()
        self.current_pos = {'X': 0, 'Y': 0, 'Z': 0}
        self.current_feed = 0
        self.debug = False
        
    def enable_debug(self):
        """Enable debug output"""
        self.debug = True
        
    def parse_nc_file(self, filename: str) -> Dict:
        """Parse NC file and calculate comprehensive cycle times"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except FileNotFoundError:
            raise FileNotFoundError(f"File '{filename}' not found!")
        except Exception as e:
            raise Exception(f"Error reading file: {e}")
            
        # Initialize counters
        machine_ops = MachineOperations()
        movement_stats = MovementStats()
        processes = []
        current_process = None
        
        if self.debug:
            print(f"Analyzing {len(lines)} lines...")
            
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
                
            # Track processes
            if line.startswith(';'):
                process_match = re.search(r'Process #(\d+)', line)
                if process_match:
                    process_num = int(process_match.group(1))
                    if process_num > 0:
                        if current_process:
                            processes.append(current_process)
                        current_process = ProcessInfo(number=process_num)
                        if self.debug and process_num <= 3:
                            print(f"Found Process #{process_num}")
                continue
                
            # Count machine operations
            self._count_machine_operations(line, machine_ops)
            
            # Extract feed rate
            feed_match = re.search(r'F(\d+\.?\d*)', line)
            if feed_match:
                self.current_feed = float(feed_match.group(1))
                
            # Process movement commands
            self._process_movements(line, movement_stats, current_process)
            
        # Add final process
        if current_process:
            processes.append(current_process)
            
        # Calculate machine overhead time
        machine_time = self._calculate_machine_time(machine_ops)
        
        # Calculate total time
        total_time = (
            machine_time +
            movement_stats.cutting_time * 60 +  # Convert to seconds
            movement_stats.rapid_time * 60      # Convert to seconds
        )
        
        # Compile results
        results = {
            'filename': filename,
            'line_count': len(lines),
            'machine_operations': machine_ops,
            'movement_stats': movement_stats,
            'processes': processes,
            'machine_time': machine_time,
            'total_time': total_time,
            'formatted_time': self._format_time(total_time),
            'config': self.config
        }
        
        if self.debug:
            self._print_debug_summary(results)
            
        return results
    
    def _count_machine_operations(self, line: str, ops: MachineOperations):
        """Count various machine operations that add to cycle time"""
        if 'CH_TOOLCHANGE.NC' in line:
            ops.tool_changes += 1
        elif 'CH_SPINDEL.NC' in line:
            # Determine if start or stop based on parameters
            if '@P2=1' in line:  # Spindle start
                ops.spindle_starts += 1
            elif '@P2=0' in line:  # Spindle stop
                ops.spindle_stops += 1
        elif 'CH_TCP_ON.NC' in line:
            ops.tcp_on += 1
        elif 'CH_TCP_OFF.NC' in line:
            ops.tcp_off += 1
        elif 'CH_CONTOUR_START.NC' in line:
            ops.contour_starts += 1
        elif 'CH_CONTOUR_END.NC' in line:
            ops.contour_ends += 1
        elif 'CH_DYNAMIC.NC' in line:
            ops.dynamic_setups += 1
        elif '#FLUSH WAIT' in line:
            ops.flush_waits += 1
        elif '#CS ON' in line or '#CS OFF' in line or '#MCS ON' in line or '#MCS OFF' in line:
            ops.coordinate_setups += 1
        elif 'L CYCLE' in line and not any(x in line for x in [
            'CH_TOOLCHANGE', 'CH_SPINDEL', 'CH_TCP_', 'CH_CONTOUR_', 'CH_DYNAMIC', 'CH_CHECK_TOOL'
        ]):
            ops.other_cycles += 1
    
    def _process_movements(self, line: str, stats: MovementStats, current_process: Optional[ProcessInfo]):
        """Process G-code movement commands"""
        # G0 - Rapid moves
        if re.search(r'\bG0\b|\bG00\b', line):
            stats.g0_moves += 1
            time, distance = self._calculate_move_time(line, self.config.rapid_speed)
            stats.rapid_time += time
            stats.total_rapid_distance += distance
            if current_process:
                current_process.moves += 1
            self._update_position(line)
            
        # G1 - Linear cutting moves
        elif re.search(r'\bG1\b|\bG01\b', line):
            stats.g1_moves += 1
            if self.current_feed > 0:
                time, distance = self._calculate_move_time(line, self.current_feed)
                stats.cutting_time += time
                stats.total_cutting_distance += distance
                if current_process:
                    current_process.cutting_time += time
                    current_process.moves += 1
            self._update_position(line)
            
        # G2/G3 - Arc moves
        elif re.search(r'\bG[0]?[23]\b', line):
            if re.search(r'\bG[0]?2\b', line):
                stats.g2_moves += 1
            else:
                stats.g3_moves += 1
                
            if self.current_feed > 0:
                time, distance = self._calculate_arc_move_time(line, self.current_feed)
                stats.cutting_time += time
                stats.total_cutting_distance += distance
                if current_process:
                    current_process.cutting_time += time
                    current_process.moves += 1
                    
                if self.debug and stats.g2_moves + stats.g3_moves <= 3:
                    print(f"Arc move {stats.g2_moves + stats.g3_moves}: {distance:.2f}mm in {time*60:.2f}s at F{self.current_feed}")
                    
            self._update_position(line)
    
    def _calculate_move_time(self, line: str, feed_rate: float) -> Tuple[float, float]:
        """Calculate time and distance for linear moves"""
        new_pos = self.current_pos.copy()
        
        # Extract coordinates
        for axis in ['X', 'Y', 'Z']:
            match = re.search(f'{axis}([-+]?\\d*\\.?\\d+)', line)
            if match:
                new_pos[axis] = float(match.group(1))
        
        # Calculate distance
        distance = math.sqrt(
            (new_pos['X'] - self.current_pos['X'])**2 +
            (new_pos['Y'] - self.current_pos['Y'])**2 +
            (new_pos['Z'] - self.current_pos['Z'])**2
        )
        
        # Calculate time in minutes
        time = distance / feed_rate if feed_rate > 0 else 0
        
        return time, distance
    
    def _calculate_arc_move_time(self, line: str, feed_rate: float) -> Tuple[float, float]:
        """Calculate time and distance for arc moves"""
        new_pos = self.current_pos.copy()
        
        # Extract coordinates
        for axis in ['X', 'Y', 'Z']:
            match = re.search(f'{axis}([-+]?\\d*\\.?\\d+)', line)
            if match:
                new_pos[axis] = float(match.group(1))
        
        # Extract radius
        r_match = re.search(r'R=([-+]?\\d*\\.?\\d+)', line)
        if r_match:
            radius = float(r_match.group(1))
            dx = new_pos['X'] - self.current_pos['X']
            dy = new_pos['Y'] - self.current_pos['Y']
            dz = new_pos['Z'] - self.current_pos['Z']
            chord_length = math.sqrt(dx**2 + dy**2 + dz**2)
            
            # Calculate arc length
            if chord_length < 0.001 and abs(radius) > 0:
                # Full circle
                arc_length = 2 * math.pi * abs(radius)
            elif chord_length > 0 and abs(radius) > 0:
                if chord_length > 2 * abs(radius):
                    arc_length = chord_length  # Fallback to chord
                else:
                    central_angle = 2 * math.asin(min(chord_length / (2 * abs(radius)), 1.0))
                    arc_length = abs(radius) * central_angle
            else:
                arc_length = chord_length
            
            # Add helical component
            if abs(dz) > 0.001:
                arc_length = math.sqrt(arc_length**2 + dz**2)
                
            distance = arc_length
        else:
            # No radius, calculate as straight line
            distance = math.sqrt(
                (new_pos['X'] - self.current_pos['X'])**2 +
                (new_pos['Y'] - self.current_pos['Y'])**2 +
                (new_pos['Z'] - self.current_pos['Z'])**2
            )
        
        # Calculate time in minutes
        time = distance / feed_rate if feed_rate > 0 else 0
        
        return time, distance
    
    def _update_position(self, line: str):
        """Update current position from G-code line"""
        for axis in ['X', 'Y', 'Z']:
            match = re.search(f'{axis}([-+]?\\d*\\.?\\d+)', line)
            if match:
                self.current_pos[axis] = float(match.group(1))
    
    def _calculate_machine_time(self, ops: MachineOperations) -> float:
        """Calculate total machine operation time"""
        return (
            ops.tool_changes * self.config.tool_change_time +
            ops.spindle_starts * self.config.spindle_start_time +
            ops.spindle_stops * self.config.spindle_stop_time +
            ops.tcp_on * self.config.tcp_on_time +
            ops.tcp_off * self.config.tcp_off_time +
            ops.contour_starts * self.config.contour_start_time +
            ops.contour_ends * self.config.contour_end_time +
            ops.dynamic_setups * self.config.dynamic_setup_time +
            ops.flush_waits * self.config.flush_wait_time +
            ops.coordinate_setups * self.config.coordinate_setup_time +
            ops.other_cycles * self.config.general_cycle_time
        )
    
    def _format_time(self, seconds: float) -> str:
        """Format time as MM:SS"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"
    
    def _print_debug_summary(self, results: Dict):
        """Print debug information"""
        ops = results['machine_operations']
        stats = results['movement_stats']
        
        print(f"\nDEBUG SUMMARY:")
        print(f"Lines processed: {results['line_count']}")
        print(f"Machine operations found:")
        print(f"  Tool changes: {ops.tool_changes}")
        print(f"  Spindle starts/stops: {ops.spindle_starts}/{ops.spindle_stops}")
        print(f"  TCP on/off: {ops.tcp_on}/{ops.tcp_off}")
        print(f"  Contour start/end: {ops.contour_starts}/{ops.contour_ends}")
        print(f"  Dynamic setups: {ops.dynamic_setups}")
        print(f"  Flush waits: {ops.flush_waits}")
        print(f"Movement counts:")
        print(f"  G0: {stats.g0_moves}, G1: {stats.g1_moves}, G2: {stats.g2_moves}, G3: {stats.g3_moves}")
        print(f"Processes found: {len(results['processes'])}")

def print_results(results: Dict):
    """Print comprehensive analysis results"""
    ops = results['machine_operations']
    stats = results['movement_stats']
    config = results['config']
    
    print(f"\n{'='*60}")
    print(f"CNC CYCLE TIME ANALYSIS: {results['filename']}")
    print(f"{'='*60}")
    
    print(f"\nFILE STATISTICS:")
    print(f"  Total lines: {results['line_count']}")
    print(f"  Processes found: {len(results['processes'])}")
    
    print(f"\nMACHINE OPERATIONS:")
    machine_time_breakdown = [
        (f"Tool changes", ops.tool_changes, config.tool_change_time),
        (f"Spindle starts", ops.spindle_starts, config.spindle_start_time),
        (f"Spindle stops", ops.spindle_stops, config.spindle_stop_time),
        (f"TCP operations", ops.tcp_on + ops.tcp_off, (config.tcp_on_time + config.tcp_off_time)/2),
        (f"Contour operations", ops.contour_starts + ops.contour_ends, (config.contour_start_time + config.contour_end_time)/2),
        (f"Dynamic setups", ops.dynamic_setups, config.dynamic_setup_time),
        (f"Flush waits", ops.flush_waits, config.flush_wait_time),
        (f"Coordinate setups", ops.coordinate_setups, config.coordinate_setup_time),
        (f"Other cycles", ops.other_cycles, config.general_cycle_time),
    ]
    
    total_machine_time = 0
    for desc, count, time_per_op in machine_time_breakdown:
        if count > 0:
            subtotal = count * time_per_op
            total_machine_time += subtotal
            print(f"  {desc}: {count} × {time_per_op:.1f}s = {subtotal:.1f}s")
    
    print(f"\nMOVEMENT ANALYSIS:")
    print(f"  Rapid moves (G0): {stats.g0_moves}")
    print(f"  Linear cuts (G1): {stats.g1_moves}")
    print(f"  Arc cuts (G2/G3): {stats.g2_moves + stats.g3_moves}")
    print(f"  Total cutting distance: {stats.total_cutting_distance:.1f}mm")
    print(f"  Total rapid distance: {stats.total_rapid_distance:.1f}mm")
    
    print(f"\nTIME BREAKDOWN:")
    print(f"  Machine operations: {total_machine_time:.1f}s")
    print(f"  Cutting time: {stats.cutting_time*60:.1f}s ({stats.cutting_time:.1f} min)")
    print(f"  Rapid time: {stats.rapid_time*60:.1f}s ({stats.rapid_time:.1f} min)")
    print(f"  {'-'*40}")
    print(f"  TOTAL CYCLE TIME: {results['total_time']:.1f}s ({results['formatted_time']})")
    
    if results['processes']:
        print(f"\nPROCESS BREAKDOWN (first 10):")
        for i, process in enumerate(results['processes'][:10]):
            process_time = process.cutting_time * 60  # Convert to seconds
            print(f"  Process {process.number:2d}: {process_time:5.1f}s ({process.moves:3d} moves)")
        if len(results['processes']) > 10:
            print(f"  ... and {len(results['processes']) - 10} more processes")

def main():
    """Main execution function"""
    if len(sys.argv) < 2:
        print("Usage: python enhanced_postprocessor.py <nc_file_path> [--debug]")
        print("Example: python enhanced_postprocessor.py Field2.nc --debug")
        sys.exit(1)
    
    nc_file_path = sys.argv[1]
    debug_mode = '--debug' in sys.argv
    
    # Create calculator with default configuration
    calculator = EnhancedCNCCycleTimeCalculator()
    
    if debug_mode:
        calculator.enable_debug()
    
    try:
        results = calculator.parse_nc_file(nc_file_path)
        print_results(results)
        
        # Additional validation info
        print(f"\nVALIDATION:")
        print(f"For comparison with actual runtime:")
        print(f"  Calculated: {results['formatted_time']}")
        print(f"  If actual runtime differs significantly, consider adjusting")
        print(f"  machine operation times in MachineConfig class")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()