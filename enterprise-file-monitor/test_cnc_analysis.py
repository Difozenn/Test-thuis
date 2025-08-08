#\!/usr/bin/env python3
import re
import os

def analyze_file(filepath):
    filename = os.path.basename(filepath)
    print(f"\n{'='*60}")
    print(f"Analyzing: {filename}")
    print(f"{'='*60}")
    
    with open(filepath, 'r', encoding='latin-1') as f:
        lines = f.readlines()
    
    tool_changes = []
    d_codes = []
    feedrates = set()
    g1_moves = []
    g0_moves = []
    current_feedrate = 0
    
    for i, line in enumerate(lines, 1):
        clean_line = line.split(';')[0].strip()
        
        # Tool changes - OPUS format
        if 'CH_TOOLCHANGE.NC' in line:
            match = re.search(r'@P4=(\d+)', line)
            if match:
                tool = int(match.group(1))
                tool_changes.append((i, 'CH_TOOLCHANGE', tool))
                
        # Tool changes - HH7 format  
        if 'CP_TC.NC' in line:
            match = re.search(r'@P4=(\d+)', line)
            if match:
                tool = int(match.group(1))
                tool_changes.append((i, 'CP_TC', tool))
                
        # Tool changes - Vision/Siemens format
        if 'C_WECHSEL' in line:
            match = re.search(r'C_WECHSEL\((\d+)', line)
            if match:
                tool = int(match.group(1))
                tool_changes.append((i, 'C_WECHSEL', tool))
        
        # D-codes (tool activations)
        match = re.search(r'^[^;]*\bD(\d{3,})\b', clean_line)
        if match:
            d_code = int(match.group(1))
            if d_code > 100:
                d_codes.append((i, d_code))
        
        # Extract feedrates
        match = re.search(r'F(\d+)', clean_line)
        if match:
            feed = int(match.group(1))
            feedrates.add(feed)
            current_feedrate = feed
            
        # Movement commands
        if re.search(r'\bG0\b|\bG00\b', clean_line):
            g0_moves.append(i)
            
        if re.search(r'\bG1\b|\bG01\b', clean_line):
            g1_moves.append((i, current_feedrate))
    
    print(f"PRIMARY Tool changes: {len(tool_changes)}")
    for line_num, change_type, tool in tool_changes:
        print(f"  Line {line_num}: {change_type} Tool {tool}")
    
    if d_codes:
        print(f"\nD-codes (tool activations): {len(d_codes)}")
        for line_num, d_code in d_codes[:5]:  # Show first 5
            print(f"  Line {line_num}: D{d_code}")
        if len(d_codes) > 5:
            print(f"  ... and {len(d_codes)-5} more")
    
    print(f"\nFeedrates used: {sorted(feedrates)}")
    print(f"G0 rapid moves: {len(g0_moves)}")
    print(f"G1 cutting moves: {len(g1_moves)}")
    
    # Calculate rough cut time
    if g1_moves:
        feeds_with_values = [f for _, f in g1_moves if f > 0]
        if feeds_with_values:
            avg_feed = sum(feeds_with_values) / len(feeds_with_values)
            print(f"\nAvg cutting feedrate: {avg_feed:.0f} mm/min")
        print(f"Tool change time: {len(tool_changes)} × 13.05s = {len(tool_changes) * 13.05:.1f}s")
    
    return {
        'file': filename,
        'tool_changes': len(tool_changes),
        'tools': [t[2] for t in tool_changes],
        'g1': len(g1_moves),
        'g0': len(g0_moves)
    }

# Test all three files
results = []
for f in ['opus.nc', 'nesting.NC', 'Field1.spf']:
    if os.path.exists(f):
        results.append(analyze_file(f))

print(f"\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")
for r in results:
    print(f"{r['file']:15} Tool Changes: {r['tool_changes']}  Tools: {r['tools']}  G1: {r['g1']}  G0: {r['g0']}")
