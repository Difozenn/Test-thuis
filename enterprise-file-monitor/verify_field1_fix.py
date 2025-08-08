#!/usr/bin/env python3
"""Verify that the Field1.spf fix is working by testing the C# analysis output"""

import json
import sys

def verify_field1_analysis():
    """
    This script can be used to verify that the C# analyzer now properly 
    detects tools and calculates timing for Field1.spf
    
    Expected results after the fix:
    - ToolChanges: 2 (was already working)
    - ToolsUsed: [602, 181] (was empty, now fixed)
    - TotalTime: ~47.5 seconds (was ~23.6s, now includes 26.1s tool change time)
    """
    
    print("Field1.spf Fix Verification")
    print("=" * 40)
    
    # Expected values after our fix
    expected = {
        'tool_changes': 2,
        'tools_used': [602, 181],  # or [17, 10] if Box mapping doesn't work
        'min_total_time': 40.0,    # Should be around 47.5s, but allow some variance
        'max_total_time': 55.0,
        'tool_change_time': 26.1   # 2 × 13.05
    }
    
    # What was broken before
    broken_symptoms = {
        'tools_used_empty': "ToolsUsed array was empty []",
        'missing_tool_time': "Total time was ~23.6s instead of ~47.5s",
        'root_cause': "EnhancedCNCAnalyzer didn't copy from ToolSessions to ToolsUsed"
    }
    
    # What the fix does
    fix_description = {
        'location': 'EnhancedCNCAnalyzer.AnalyzeFileAsync() method',
        'added_code': '''
// Ensure ToolsUsed is populated from ToolSessions if empty
if (result.ToolsUsed.Count == 0 && result.ToolSessions.Count > 0)
{
    result.ToolsUsed = result.ToolSessions.Keys.ToList();
    Console.WriteLine($"[ENHANCED] Fixed ToolsUsed from sessions: {string.Join(", ", result.ToolsUsed)}");
}''',
        'result': 'ToolsUsed now populated from ToolSessions when EnhancedCNCAnalyzer is used'
    }
    
    print("WHAT WAS BROKEN:")
    for key, value in broken_symptoms.items():
        print(f"  • {value}")
    
    print(f"\nTHE FIX:")
    print(f"  Location: {fix_description['location']}")
    print(f"  Result: {fix_description['result']}")
    
    print(f"\nEXPECTED RESULTS AFTER FIX:")
    print(f"  Tool Changes: {expected['tool_changes']}")
    print(f"  Tools Used: {expected['tools_used']}")
    print(f"  Tool Change Time: {expected['tool_change_time']}s")
    print(f"  Total Time Range: {expected['min_total_time']:.1f}s - {expected['max_total_time']:.1f}s")
    
    print(f"\nTO TEST THE FIX:")
    print(f"  1. Build the C# project")
    print(f"  2. Analyze Field1.spf")
    print(f"  3. Check that ToolsUsed contains [602, 181] or [17, 10]")
    print(f"  4. Check that TotalTime is between {expected['min_total_time']:.1f}s and {expected['max_total_time']:.1f}s")
    print(f"  5. Look for debug message: '[ENHANCED] Fixed ToolsUsed from sessions: ...'")
    
    return expected

def test_against_actual_results(actual_tools, actual_total_time_seconds, actual_tool_changes):
    """Test the actual C# analysis results against expectations"""
    expected = verify_field1_analysis()
    
    print(f"\n" + "="*50)
    print("ACTUAL vs EXPECTED COMPARISON")
    print("="*50)
    
    # Test tool changes
    tool_changes_ok = actual_tool_changes == expected['tool_changes']
    print(f"Tool Changes: {actual_tool_changes} {'✅' if tool_changes_ok else '❌'} (expected: {expected['tool_changes']})")
    
    # Test tools used
    tools_ok = len(actual_tools) == len(expected['tools_used']) and len(actual_tools) > 0
    tools_str = str(actual_tools) if actual_tools else "[]"
    print(f"Tools Used: {tools_str} {'✅' if tools_ok else '❌'} (expected: {expected['tools_used']} or similar)")
    
    # Test total time
    time_ok = expected['min_total_time'] <= actual_total_time_seconds <= expected['max_total_time']
    print(f"Total Time: {actual_total_time_seconds:.1f}s {'✅' if time_ok else '❌'} (expected: {expected['min_total_time']:.1f}s - {expected['max_total_time']:.1f}s)")
    
    # Overall result
    all_ok = tool_changes_ok and tools_ok and time_ok
    print(f"\nOVERALL: {'✅ FIX SUCCESSFUL' if all_ok else '❌ STILL ISSUES'}")
    
    if not all_ok:
        print("\nSTILL FAILING:")
        if not tool_changes_ok:
            print("  • Tool changes not detected correctly")
        if not tools_ok:
            print("  • Tools list still empty or incorrect")
        if not time_ok:
            print("  • Total time still incorrect (missing tool change time)")
    
    return all_ok

if __name__ == "__main__":
    if len(sys.argv) >= 4:
        # Test mode - compare actual results
        tools = eval(sys.argv[1])  # e.g., [602, 181]
        total_time = float(sys.argv[2])  # e.g., 47.5
        tool_changes = int(sys.argv[3])  # e.g., 2
        test_against_actual_results(tools, total_time, tool_changes)
    else:
        # Explanation mode
        verify_field1_analysis()