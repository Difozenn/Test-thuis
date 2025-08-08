#!/usr/bin/env python3
"""
Test why Field1.spf shows 0 tools
"""

import re

def test_tool_detection():
    print("Testing Field1.spf tool detection")
    print("=" * 50)
    
    # Read the file
    with open('Field1.spf', 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    # 1. Check Platz to Box mapping
    print("\n1. PLATZ TO BOX MAPPING:")
    print("-" * 30)
    platz_to_box = {}
    
    for line in lines:
        if "Box:" in line and "Platz:" in line:
            # Try the C# regex pattern
            box_match = re.search(r'Box:\s*(\d+)', line)
            platz_match = re.search(r'Platz:(\d+)', line)
            
            if box_match and platz_match:
                box_id = int(box_match.group(1))
                platz_num = int(platz_match.group(1))
                platz_to_box[platz_num] = box_id
                print(f"  Line: {line.strip()}")
                print(f"  Mapped: Platz {platz_num} → Box {box_id}")
    
    if not platz_to_box:
        print("  ❌ NO MAPPINGS FOUND!")
    else:
        print(f"\n  ✅ Found {len(platz_to_box)} mappings: {platz_to_box}")
    
    # 2. Check C_WECHSEL detection
    print("\n2. C_WECHSEL TOOL CHANGES:")
    print("-" * 30)
    tool_changes = []
    
    for i, line in enumerate(lines, 1):
        if "C_WECHSEL" in line:
            # Try the C# regex pattern
            match = re.search(r'C_WECHSEL\((\d+)', line)
            if match:
                platz_num = int(match.group(1))
                actual_tool = platz_to_box.get(platz_num, platz_num)
                tool_changes.append((i, platz_num, actual_tool))
                print(f"  Line {i}: {line.strip()}")
                print(f"    Platz {platz_num} → Tool {actual_tool}")
    
    if not tool_changes:
        print("  ❌ NO TOOL CHANGES FOUND!")
    else:
        print(f"\n  ✅ Found {len(tool_changes)} tool changes")
        print(f"  Tools used: {[t[2] for t in tool_changes]}")
    
    # 3. Check why timing might be wrong
    print("\n3. TIMING ANALYSIS:")
    print("-" * 30)
    
    # Count movements
    g0_count = 0
    g1_count = 0
    g2_count = 0
    g3_count = 0
    
    for line in lines:
        # Remove comments
        if ';' in line:
            line = line[:line.index(';')]
        line = line.strip().upper()
        
        if re.search(r'\bG0\d?\b', line):
            g0_count += 1
        elif re.search(r'\bG0?1\b', line):
            g1_count += 1
        elif re.search(r'\bG0?2\b', line):
            g2_count += 1
        elif re.search(r'\bG0?3\b', line):
            g3_count += 1
    
    print(f"  G0 rapids: {g0_count}")
    print(f"  G1 linear: {g1_count}")
    print(f"  G2 CW arcs: {g2_count}")
    print(f"  G3 CCW arcs: {g3_count}")
    
    # Calculate expected timing
    tool_change_time = len(tool_changes) * 13.05
    # Very rough estimate
    cutting_time = (g1_count + g2_count + g3_count) * 0.5  # 0.5s per move average
    rapid_time = g0_count * 0.2  # 0.2s per rapid average
    
    total = tool_change_time + cutting_time + rapid_time
    
    print(f"\n  Estimated timing:")
    print(f"    Tool changes: {tool_change_time:.1f}s ({len(tool_changes)} × 13.05s)")
    print(f"    Cutting: ~{cutting_time:.1f}s (rough estimate)")
    print(f"    Rapids: ~{rapid_time:.1f}s (rough estimate)")
    print(f"    TOTAL: ~{total:.1f}s")
    
    # 4. Check what's being sent to the server
    print("\n4. EXPECTED SERVER DATA:")
    print("-" * 30)
    print(f"  ToolChanges: {len(tool_changes)}")
    print(f"  ToolsUsed: {[t[2] for t in tool_changes] if tool_changes else []}")
    print(f"  TotalTime: ~{total/60:.2f} minutes")
    
    return {
        'mappings': platz_to_box,
        'tool_changes': len(tool_changes),
        'tools': [t[2] for t in tool_changes] if tool_changes else [],
        'total_time': total
    }

if __name__ == "__main__":
    result = test_tool_detection()
    
    print("\n" + "=" * 50)
    print("DIAGNOSIS:")
    print("=" * 50)
    
    if result['tool_changes'] == 0:
        print("❌ PROBLEM: No tool changes detected!")
        print("   - Check if C_WECHSEL regex is matching")
        print("   - Check if file is being read correctly")
    elif not result['tools']:
        print("❌ PROBLEM: Tool changes found but no tools in list!")
        print("   - Check if tools are being added to ToolsUsed")
    elif result['total_time'] < 30:
        print("⚠️  PROBLEM: Timing too low!")
        print("   - Movement detection may be incomplete")
        print("   - Modal G-codes not being handled")
    else:
        print("✅ Everything looks correct!")
    
    print(f"\nExpected: 2 tool changes, tools [602, 181], ~39.5s total")
    print(f"Actual:   {result['tool_changes']} tool changes, tools {result['tools']}, ~{result['total_time']:.1f}s total")