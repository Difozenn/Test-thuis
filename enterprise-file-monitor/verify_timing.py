#!/usr/bin/env python3
"""Verify expected timing for Field1.spf"""

# Expected values from TCALC
tool_changes = 2
tool_change_time_per = 13.05  # seconds per tool change
cutting_time = 10.3  # seconds
rapid_time = 3.2  # seconds

# Calculate total
tool_change_total = tool_changes * tool_change_time_per
total_time = tool_change_total + cutting_time + rapid_time

print(f"Expected timing for Field1.spf:")
print(f"  Tool changes: {tool_changes} × {tool_change_time_per}s = {tool_change_total:.1f}s")
print(f"  Cutting time: {cutting_time:.1f}s")
print(f"  Rapid time: {rapid_time:.1f}s")
print(f"  Total time: {total_time:.1f}s ({total_time/60:.2f} min)")
print()

# What we're actually getting
actual_total = 23.59  # seconds from the debug output
actual_tool_time = 12.94 + 9.19  # T602 + T181

print(f"Actual timing from C#:")
print(f"  Total time: {actual_total:.1f}s")
print(f"  Tool session time: {actual_tool_time:.1f}s")
print(f"  Missing time: {total_time - actual_total:.1f}s")
print()

# Check if tool change time is missing
if abs(total_time - actual_total - tool_change_total) < 1:
    print("ERROR: Tool change time is not being added!")
elif actual_total < total_time - 5:
    print("ERROR: Some movements or time is missing!")
else:
    print("Timing looks correct")