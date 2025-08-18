#!/usr/bin/env python3
"""
Verify T501 drilling operations in OPUS files to calculate expected overhead
"""

import re
import sys

def analyze_opus_file(filename):
    """Analyze an OPUS file for T501 drilling operations"""
    print(f"\nAnalyzing {filename}...")
    
    with open(filename, 'r') as f:
        lines = f.readlines()
    
    # Count drilling operations
    drill_count_f600 = 0
    drill_count_f1000 = 0
    drill_count_f2000 = 0
    drill_count_f2500 = 0
    drill_count_f3500 = 0
    total_drill_ops = 0
    ch_drillhead_count = 0
    cs_on_count = 0
    cs_off_count = 0
    
    current_tool = 0
    current_feedrate = 0
    
    for i, line in enumerate(lines):
        # Track tool changes
        if 'CH_TOOLCHANGE.NC' in line and '@P4=' in line:
            tool_match = re.search(r'@P4=(\d+)', line)
            if tool_match:
                current_tool = int(tool_match.group(1))
                print(f"  Tool change to T{current_tool} at line {i+1}")
        
        # Track feedrate changes
        f_match = re.search(r'\bF(\d+)', line)
        if f_match:
            current_feedrate = int(f_match.group(1))
        
        # Count CH_DRILLHEAD operations
        if 'CH_DRILLHEAD.NC' in line:
            ch_drillhead_count += 1
        
        # Count coordinate system operations
        if '#CS ON' in line:
            cs_on_count += 1
        elif '#CS OFF' in line:
            cs_off_count += 1
        
        # Count drilling operations for T501
        # Only count the deepest drilling move (final plunge) to avoid double counting
        if current_tool == 501:
            # Look for drilling moves - the deepest Z move with specific drilling feedrates
            if re.search(r'Z\s*=?\s*-', line) and 'G1' in line:
                # Check if this is a final drilling move (typically deeper than -5)
                z_match = re.search(r'Z\s*=?\s*([-\d.]+)', line)
                if z_match:
                    z_depth = float(z_match.group(1))
                    # Count only deep drilling moves (final plunge), not entry moves
                    if z_depth < -5 or (z_depth < -0.5 and current_feedrate == 2500):
                        total_drill_ops += 1
                        if current_feedrate == 600:
                            drill_count_f600 += 1
                        elif current_feedrate == 1000:
                            drill_count_f1000 += 1
                        elif current_feedrate == 2000:
                            drill_count_f2000 += 1
                        elif current_feedrate == 2500:
                            drill_count_f2500 += 1
                        elif current_feedrate == 3500:
                            drill_count_f3500 += 1
    
    print(f"\nT501 Drilling Operations:")
    print(f"  F600:  {drill_count_f600} operations")
    print(f"  F1000: {drill_count_f1000} operations")
    print(f"  F2000: {drill_count_f2000} operations")
    print(f"  F2500: {drill_count_f2500} operations")
    print(f"  F3500: {drill_count_f3500} operations")
    print(f"  Total: {total_drill_ops} drilling operations")
    
    print(f"\nOPUS-specific operations:")
    print(f"  CH_DRILLHEAD cycles: {ch_drillhead_count}")
    print(f"  #CS ON operations: {cs_on_count}")
    print(f"  #CS OFF operations: {cs_off_count}")
    
    # Calculate expected overhead
    opus_overhead = total_drill_ops * 1.2  # 1.2s per drilling operation
    print(f"\nExpected OPUS overhead: {opus_overhead:.1f} seconds ({opus_overhead/60:.2f} minutes)")
    
    # Extract expected time from filename
    if '_' in filename:
        parts = filename.replace('.nc', '').split('_')
        if len(parts) >= 3:
            try:
                expected_min = int(parts[-2])
                expected_sec = int(parts[-1])
                expected_total = expected_min * 60 + expected_sec
                print(f"Expected total time from filename: {expected_min}:{expected_sec:02d} ({expected_total} seconds)")
            except:
                pass
    
    return total_drill_ops, opus_overhead

# Test files
files_to_test = ['opus_6_45.nc', 'opus_2_55.nc', 'opus_1_05.nc']

print("=" * 60)
print("OPUS T501 Drilling Analysis")
print("=" * 60)

total_overhead = 0
for file in files_to_test:
    try:
        ops, overhead = analyze_opus_file(file)
        total_overhead += overhead
    except FileNotFoundError:
        print(f"\nFile {file} not found - skipping")
    except Exception as e:
        print(f"\nError analyzing {file}: {e}")

print("\n" + "=" * 60)
print(f"Total OPUS overhead for all files: {total_overhead:.1f} seconds")
print("=" * 60)