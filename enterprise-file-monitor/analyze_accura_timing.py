#!/usr/bin/env python3
"""
Analyze SystemLog.bk5 to understand machine timing and runtime
"""

import re
from datetime import datetime, timedelta

def parse_time(time_str):
    """Parse time string HH:MM:SS to datetime"""
    parts = time_str.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = int(parts[2]) if len(parts) > 2 else 0
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)

def analyze_log_file(filename):
    """Analyze log file for timing patterns"""
    
    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    # Track entries and timing
    entries = []
    date_str = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check for date line
        if re.match(r'^\d{2}\.\d{2}\.\d{4}$', line):
            date_str = line
            continue
        
        # Check for production entry
        if 'M1 von KAM1 Retour1' in line:
            time_match = re.match(r'^(\d{2}:\d{2}:\d{2})', line)
            if time_match:
                time_str = time_match.group(1)
                
                # Extract BC and B values
                bc_match = re.search(r'BC=\s*(\d+)', line)
                b_match = re.search(r'B=\s*(\d+)', line)
                
                if bc_match and b_match:
                    bc = int(bc_match.group(1))
                    width = int(b_match.group(1))
                    
                    entries.append({
                        'time': parse_time(time_str),
                        'bc': bc,
                        'width': width,
                        'line': line
                    })
    
    # Analyze timing patterns
    print(f"Analyzing {filename}")
    print(f"Date: {date_str}")
    print(f"Total entries: {len(entries)}")
    print()
    
    if len(entries) > 1:
        # Calculate time differences
        time_diffs = []
        gaps_over_1min = []
        
        for i in range(1, len(entries)):
            diff = (entries[i]['time'] - entries[i-1]['time']).total_seconds()
            time_diffs.append(diff)
            
            if diff > 60:  # Gap over 1 minute
                gaps_over_1min.append({
                    'index': i,
                    'from_bc': entries[i-1]['bc'],
                    'to_bc': entries[i]['bc'],
                    'from_time': entries[i-1]['time'],
                    'to_time': entries[i]['time'],
                    'gap_seconds': diff
                })
        
        # Calculate statistics
        avg_diff = sum(time_diffs) / len(time_diffs)
        min_diff = min(time_diffs)
        max_diff = max(time_diffs)
        
        # Filter for normal operation (15-25 seconds)
        normal_diffs = [d for d in time_diffs if 15 <= d <= 25]
        if normal_diffs:
            avg_normal = sum(normal_diffs) / len(normal_diffs)
        else:
            avg_normal = 0
        
        print("Time between consecutive entries:")
        print(f"  Average: {avg_diff:.1f} seconds")
        print(f"  Min: {min_diff:.1f} seconds")
        print(f"  Max: {max_diff:.1f} seconds")
        print(f"  Average during normal operation (15-25s): {avg_normal:.1f} seconds")
        print(f"  Entries with normal timing (15-25s): {len(normal_diffs)} of {len(time_diffs)}")
        print()
        
        # Calculate total runtime
        first_time = entries[0]['time']
        last_time = entries[-1]['time']
        total_duration = (last_time - first_time).total_seconds()
        
        print(f"Work period:")
        print(f"  Start: {first_time}")
        print(f"  End: {last_time}")
        print(f"  Total duration: {total_duration/3600:.2f} hours")
        print()
        
        # Calculate actual machine time (20s per narrow piece, 60s per wide piece)
        narrow_count = sum(1 for e in entries if e['width'] < 2400)
        wide_count = sum(1 for e in entries if e['width'] >= 2400)
        machine_time_seconds = narrow_count * 20 + wide_count * 60
        
        print(f"Machine time calculation:")
        print(f"  Narrow pieces (B < 2400): {narrow_count} × 20s = {narrow_count * 20}s")
        print(f"  Wide pieces (B >= 2400): {wide_count} × 60s = {wide_count * 60}s")
        print(f"  Total machine time: {machine_time_seconds}s = {machine_time_seconds/60:.1f} minutes = {machine_time_seconds/3600:.2f} hours")
        print()
        
        # Show gaps (machine stops)
        if gaps_over_1min:
            print(f"Machine stops (gaps > 1 minute): {len(gaps_over_1min)}")
            total_stop_time = sum(g['gap_seconds'] for g in gaps_over_1min)
            print(f"Total stop time: {total_stop_time/60:.1f} minutes = {total_stop_time/3600:.2f} hours")
            print("\nLargest gaps:")
            for gap in sorted(gaps_over_1min, key=lambda x: x['gap_seconds'], reverse=True)[:5]:
                print(f"  BC {gap['from_bc']} → {gap['to_bc']}: {gap['gap_seconds']/60:.1f} min gap ({gap['from_time']} → {gap['to_time']})")
        
        # Analyze 6-piece loop pattern
        print("\n6-Piece Loop Analysis:")
        loop_times = []
        for i in range(0, len(entries) - 6, 6):
            # Look at every 6 pieces
            loop_start = entries[i]['time']
            loop_end = entries[i + 5]['time']
            loop_duration = (loop_end - loop_start).total_seconds()
            
            # Check if this is a continuous loop (no large gaps)
            has_gap = False
            for j in range(i, i + 5):
                diff = (entries[j + 1]['time'] - entries[j]['time']).total_seconds()
                if diff > 30:  # More than 30 seconds between pieces
                    has_gap = True
                    break
            
            if not has_gap:
                loop_times.append(loop_duration)
        
        if loop_times:
            avg_loop_time = sum(loop_times) / len(loop_times)
            print(f"  Continuous 6-piece loops found: {len(loop_times)}")
            print(f"  Average time for 6-piece loop: {avg_loop_time:.1f} seconds = {avg_loop_time/60:.1f} minutes")
            print(f"  Average time per piece in loop: {avg_loop_time/6:.1f} seconds")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = '/mnt/c/Users/Rob_v/Desktop/Test-thuis/enterprise-file-monitor/accura/SystemLog.bk5'
    
    analyze_log_file(filename)