#!/usr/bin/env python3
"""
Full test showing the CNC analysis detecting tool changes from all 3 postprocessors
"""

import re

def analyze_file(filename, description):
    """Analyze a CNC file and show tool changes detected"""
    
    print(f"\n{'='*60}")
    print(f"Analyzing: {filename}")
    print(f"Format: {description}")
    print(f"{'='*60}")
    
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except:
        with open(filename, 'r', encoding='latin-1') as f:
            lines = f.readlines()
    
    tool_changes = []
    current_tool = 0
    tools_used = set()
    
    for i, line in enumerate(lines, 1):
        # 1. OPUS format: CH_TOOLCHANGE.NC
        if "CH_TOOLCHANGE.NC" in line:
            match = re.search(r"@P4=(\d+)", line)
            if match:
                tool_num = int(match.group(1))
                tool_changes.append(f"Line {i}: OPUS tool change to T{tool_num}")
                tools_used.add(tool_num)
                current_tool = tool_num
        
        # 2. HH7/Nesting format: CP_TC.NC
        elif "CP_TC.NC" in line:
            match = re.search(r"@P4=(\d+)", line)
            if match:
                tool_num = int(match.group(1))
                tool_changes.append(f"Line {i}: HH7 tool change to T{tool_num}")
                tools_used.add(tool_num)
                current_tool = tool_num
        
        # 3. Vision/Siemens format: C_WECHSEL
        elif "C_WECHSEL" in line:
            match = re.search(r"C_WECHSEL\((\d+)", line)
            if match:
                tool_num = int(match.group(1))
                tool_changes.append(f"Line {i}: Vision tool change to T{tool_num}")
                tools_used.add(tool_num)
                current_tool = tool_num
        
        # 4. OPUS D-code tool selection (D601, D181, etc)
        else:
            # Only look for D-codes at start of line (not in comments)
            if not line.strip().startswith(";"):
                match = re.search(r"^\s*N?\d*\s*D(\d{3,})\b", line)
                if match:
                    tool_num = int(match.group(1))
                    if tool_num > 100 and tool_num != current_tool:
                        tool_changes.append(f"Line {i}: OPUS D-code change to D{tool_num}")
                        tools_used.add(tool_num)
                        current_tool = tool_num
        
        # 5. Standard T-code with D compensation
        t_match = re.search(r"\bT(\d+)\s+D\d+", line, re.IGNORECASE)
        if t_match and "; --- SpeedCall" not in line:
            tool_num = int(t_match.group(1))
            if tool_num != current_tool:
                # Check if it looks like a real tool change context
                if i > 1 and i < len(lines):
                    context = lines[max(0, i-3):min(len(lines), i+2)]
                    context_str = ''.join(context)
                    if any(x in context_str for x in ["TC.NC", "HEAD", "Platz:", "TOOL"]):
                        tool_changes.append(f"Line {i}: T-code change to T{tool_num}")
                        tools_used.add(tool_num)
                        current_tool = tool_num
    
    # Display results
    print("\nTool Changes Detected:")
    print("-" * 40)
    if tool_changes:
        for change in tool_changes:
            print(f"  {change}")
    else:
        print("  No tool changes found")
    
    print(f"\nSummary:")
    print(f"  Total tool changes: {len(tool_changes)}")
    print(f"  Tools used: {sorted(tools_used)}")
    print(f"  File lines: {len(lines)}")
    
    # Check for expected result
    if len(tool_changes) == 2:
        print(f"  ✓ CORRECT: Found expected 2 tool changes")
    else:
        print(f"  ✗ WARNING: Expected 2 tool changes but found {len(tool_changes)}")
    
    # Show sample cutting operations
    print("\nSample Operations Found:")
    print("-" * 40)
    g_codes = {"G0": 0, "G1": 0, "G2": 0, "G3": 0}
    for line in lines:
        for code in g_codes:
            if re.search(rf"\b{code}\b", line):
                g_codes[code] += 1
    
    print(f"  Rapid moves (G0): {g_codes['G0']}")
    print(f"  Linear cuts (G1): {g_codes['G1']}")
    print(f"  Arc CW (G2): {g_codes['G2']}")
    print(f"  Arc CCW (G3): {g_codes['G3']}")
    
    total_cuts = g_codes['G1'] + g_codes['G2'] + g_codes['G3']
    print(f"  Total cutting moves: {total_cuts}")
    print(f"  Total rapid moves: {g_codes['G0']}")

# Test all three files
files = [
    ("opus.nc", "OPUS postprocessor (RB_OPUS_V7)"),
    ("nesting.NC", "HH7/Nesting postprocessor"),
    ("Field1.spf", "Vision/Siemens postprocessor")
]

print("CNC Analysis Tool Change Detection Test")
print("Testing 3 different postprocessor formats")

for filename, description in files:
    analyze_file(filename, description)

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)