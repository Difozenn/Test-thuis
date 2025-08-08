#!/usr/bin/env python3
"""Check the actual tool change count in the analysis results"""

import json
import sys

# Expected values
expected_tool_changes = 2
expected_tool_change_time = 26.1  # 2 × 13.05s
expected_total_time = 39.5  # seconds

# Actual values from output
actual_total_seconds = 23.59
actual_tools = ["T602", "T181"]

print("Field1.spf Analysis Check:")
print("=" * 40)
print(f"Tools detected: {actual_tools} ✓")
print(f"Expected tool changes: {expected_tool_changes}")
print(f"Expected tool change time: {expected_tool_change_time}s")
print()
print(f"Actual total time: {actual_total_seconds}s")
print(f"Expected total time: {expected_total_time}s")
print(f"Missing time: {expected_total_time - actual_total_seconds:.1f}s")
print()

# Check if tool change time is missing
if abs(expected_tool_change_time - (expected_total_time - actual_total_seconds)) < 2:
    print("❌ PROBLEM: Tool change time is NOT being added to total!")
    print(f"   The {expected_tool_change_time}s for tool changes is missing")
    print()
    print("Likely issue in FileMonitorTrayApp.cs:")
    print("1. analysis.ToolChanges is 0 (not counting C_WECHSEL)")
    print("2. TC_51_51 is not 13.05")
    print("3. toolChangeTime is not added to totalCycleTimeSeconds")
else:
    print("⚠️ PROBLEM: Something else is wrong with timing calculation")