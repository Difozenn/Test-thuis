#!/usr/bin/env python3
"""Test tool change detection in Field1.spf"""

import re

def analyze_field1():
    with open('Field1.spf', 'r', encoding='latin-1') as f:
        lines = f.readlines()
    
    # Build Platz to Box mapping
    platz_to_box = {}
    for line in lines:
        if 'Box:' in line and 'Platz:' in line:
            box_match = re.search(r'Box:\s*(\d+)', line)
            platz_match = re.search(r'Platz:(\d+)', line)
            if box_match and platz_match:
                box_id = int(box_match.group(1))
                platz_id = int(platz_match.group(1))
                platz_to_box[platz_id] = box_id
                print(f"Mapping: Platz {platz_id} -> Box {box_id}")
    
    print(f"\nPlatz to Box mapping: {platz_to_box}")
    
    # Find C_WECHSEL tool changes
    tool_changes = 0
    tools_used = []
    
    for i, line in enumerate(lines, 1):
        if 'C_WECHSEL' in line:
            match = re.search(r'C_WECHSEL\((\d+)', line)
            if match:
                platz = int(match.group(1))
                if platz in platz_to_box:
                    tool = platz_to_box[platz]
                    print(f"Line {i}: C_WECHSEL({platz}) -> Tool {tool}")
                    tool_changes += 1
                    if tool not in tools_used:
                        tools_used.append(tool)
    
    print(f"\nTotal tool changes: {tool_changes}")
    print(f"Tools used: {tools_used}")
    
    # Calculate expected time
    tool_change_time = tool_changes * 13.05
    print(f"\nTool change time: {tool_changes} × 13.05s = {tool_change_time:.1f}s")
    
    return tool_changes, tools_used

if __name__ == "__main__":
    analyze_field1()