import re
import math
from pathlib import Path

def analyze_file(filepath):
    print(f'\n{"="*60}')
    print(f'Analyzing: {filepath}')
    print('='*60)
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    tool_changes = []
    tools_used = set()
    movements = {'G0': [], 'G1': [], 'G2': [], 'G3': []}
    tool_mapping = {}
    
    current_tool = None
    current_feedrate = 3000
    current_x, current_y, current_z = 0, 0, 0
    
    # Find tool mappings for SPF
    if filepath.endswith('.spf'):
        for line in lines:
            if 'Box:' in line and 'Platz:' in line:
                box_match = re.search(r'Box:\s*(\d+)', line)
                platz_match = re.search(r'Platz:(\d+)', line)
                if box_match and platz_match:
                    platz = int(platz_match.group(1))
                    box = int(box_match.group(1))
                    tool_mapping[platz] = box
                    print(f'  Mapping: Platz {platz} -> Tool {box}')
    
    # Analyze program
    for i, line in enumerate(lines, 1):
        clean_line = line.split(';')[0].strip()
        if not clean_line:
            continue
            
        # C_WECHSEL for Vision/Siemens
        if 'C_WECHSEL' in line:
            match = re.search(r'C_WECHSEL\((\d+)', line)
            if match:
                platz = int(match.group(1))
                tool = tool_mapping.get(platz, platz)
                tool_changes.append({'line': i, 'tool': tool})
                tools_used.add(tool)
                current_tool = tool
                print(f'  Line {i}: C_WECHSEL({platz}) -> T{tool}')
                
        # CP_TC for HH7
        elif 'CP_TC.NC' in line:
            match = re.search(r'@P4=(\d+)', line)
            if match:
                tool = int(match.group(1))
                tool_changes.append({'line': i, 'tool': tool})
                tools_used.add(tool)
                current_tool = tool
                print(f'  Line {i}: CP_TC -> T{tool}')
                
        # CH_TOOLCHANGE for OPUS
        elif 'CH_TOOLCHANGE.NC' in line:
            match = re.search(r'@P4=(\d+)', line)
            if match:
                tool = int(match.group(1))
                tool_changes.append({'line': i, 'tool': tool})
                tools_used.add(tool)
                current_tool = tool
                print(f'  Line {i}: CH_TOOLCHANGE -> T{tool}')
        
        # D-codes (OPUS)
        d_match = re.search(r'\bD(\d{3,})\b', clean_line)
        if d_match:
            d_num = int(d_match.group(1))
            if d_num \!= current_tool:
                current_tool = d_num
                print(f'  Line {i}: D{d_num} activation')
                
        # Feedrates
        f_match = re.search(r'F([\d.]+)', clean_line)
        if f_match:
            current_feedrate = float(f_match.group(1))
            
        # Movements
        for gcode in ['G0', 'G00', 'G1', 'G01', 'G2', 'G02', 'G3', 'G03']:
            if re.search(rf'\b{gcode}\b', clean_line):
                x_match = re.search(r'X([-+]?[\d.]+)', clean_line)
                y_match = re.search(r'Y([-+]?[\d.]+)', clean_line)
                z_match = re.search(r'Z([-+]?[\d.]+)', clean_line)
                
                new_x = float(x_match.group(1)) if x_match else current_x
                new_y = float(y_match.group(1)) if y_match else current_y
                new_z = float(z_match.group(1)) if z_match else current_z
                
                distance = math.sqrt(
                    (new_x - current_x)**2 + 
                    (new_y - current_y)**2 + 
                    (new_z - current_z)**2
                )
                
                if gcode in ['G0', 'G00']:
                    z_dist = abs(new_z - current_z)
                    xy_dist = math.sqrt((new_x - current_x)**2 + (new_y - current_y)**2)
                    feedrate = 20000 if z_dist > xy_dist * 2 else 30000
                    gcode_type = 'G0'
                else:
                    feedrate = current_feedrate
                    gcode_type = gcode[0:2]
                
                time_sec = (distance / feedrate * 60) if feedrate > 0 else 0
                
                movements[gcode_type].append({
                    'line': i,
                    'distance': distance,
                    'time_sec': time_sec,
                    'tool': current_tool
                })
                
                if distance > 1:
                    print(f'  Line {i}: {gcode_type} dist={distance:.1f}mm, time={time_sec:.2f}s, T{current_tool}')
                
                current_x, current_y, current_z = new_x, new_y, new_z
                break
    
    # Summary
    total_g0 = sum(m['time_sec'] for m in movements['G0'])
    total_g1 = sum(m['time_sec'] for m in movements['G1'])
    total_g2 = sum(m['time_sec'] for m in movements['G2'])
    total_g3 = sum(m['time_sec'] for m in movements['G3'])
    tool_change_time = len(tool_changes) * 13.05
    
    print(f'\nSUMMARY for {filepath}:')
    print(f'  Tool changes: {len(tool_changes)} = {tool_change_time:.1f}s')
    print(f'  Tools: {sorted(tools_used)}')
    print(f'  G0 time: {total_g0:.1f}s')
    print(f'  G1 time: {total_g1:.1f}s')
    print(f'  G2 time: {total_g2:.1f}s')
    print(f'  G3 time: {total_g3:.1f}s')
    print(f'  Movement time: {total_g0 + total_g1 + total_g2 + total_g3:.1f}s')
    print(f'  TOTAL: {total_g0 + total_g1 + total_g2 + total_g3 + tool_change_time:.1f}s')

# Analyze all files
for file in ['Field1.spf', 'nesting.NC', 'opus.nc']:
    if Path(file).exists():
        analyze_file(file)
