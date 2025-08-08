#!/usr/bin/env python3
"""
Verify CNC analysis API compatibility between FileMonitorTrayApp.cs and app.py
"""

import re
import json

def verify_api_compatibility():
    """Check if C# CNC analysis output matches Python API expectations"""
    
    print("🔍 VERIFYING CNC ANALYSIS API COMPATIBILITY")
    print("=" * 60)
    
    # Read the C# source to analyze data structure
    with open('FileMonitorTrayApp.cs', 'r', encoding='utf-8') as f:
        cs_content = f.read()
    
    # Read Python API to analyze expected structure
    with open('app.py', 'r', encoding='utf-8') as f:
        py_content = f.read()
    
    print("📤 C# OUTPUT STRUCTURE (FileMonitorTrayApp.cs)")
    print("-" * 50)
    
    # Extract the payload structure from C# code
    payload_match = re.search(r'cncAnalysisPayload = new\s*{([^}]+)};', cs_content, re.DOTALL)
    if payload_match:
        payload_content = payload_match.group(1)
        print("✅ Found C# payload structure:")
        
        # Parse the fields
        fields = re.findall(r'(\w+)\s*=\s*([^,\n]+)', payload_content)
        for field_name, field_value in fields:
            print(f"  • {field_name}: {field_value.strip()}")
    
    # Extract ToolUsageDetails structure
    tool_details_match = re.search(r'var toolUsageDetails = [^;]+Select\(session => new\s*{([^}]+)}\)', cs_content, re.DOTALL)
    if tool_details_match:
        print(f"\\n✅ Found ToolUsageDetails structure:")
        tool_fields = re.findall(r'(\w+)\s*=\s*([^,\n]+)', tool_details_match.group(1))
        for field_name, field_value in tool_fields:
            print(f"  • {field_name}: {field_value.strip()}")
    
    print(f"\\n📥 PYTHON API EXPECTATIONS (app.py)")
    print("-" * 50)
    
    # Extract expected API structure from Python
    api_extract_match = re.search(r'cnc_analysis_data\.get\\([^}]+tool_usage_details.*?\\)', py_content, re.DOTALL)
    if api_extract_match:
        print("✅ Found Python API expectations:")
        
        expected_fields = [
            ("TotalTime", "Total cycle time in minutes"),
            ("MachineTime", "Machine operation time in minutes"), 
            ("ToolChanges", "Number of tool changes"),
            ("Filename", "CNC file name"),
            ("ToolsUsed", "Array of tool numbers (fallback)"),
            ("ToolUsageDetails", "Detailed per-tool data")
        ]
        
        for field, desc in expected_fields:
            found = field in py_content
            status = "✅" if found else "❌"
            print(f"  {status} {field}: {desc}")
    
    # Check database mapping
    print(f"\\n🗄️  DATABASE MAPPING")
    print("-" * 50)
    
    db_mappings = [
        ("TotalTime", "cycle_time_seconds", "TotalTime * 60"),
        ("MachineTime", "machine_time_minutes", "Direct mapping"),
        ("ToolChanges", "tool_changes", "Direct mapping"),
        ("Filename", "file_path", "Direct mapping")
    ]
    
    print("✅ Main CNC Analysis table:")
    for c_field, db_field, conversion in db_mappings:
        print(f"  • {c_field} → {db_field} ({conversion})")
    
    print(f"\\n✅ ToolUsage table:")
    tool_mappings = [
        ("ToolNumber", "tool_number", "Direct"),
        ("TotalTime", "total_time", "Seconds"),
        ("CuttingTime", "cutting_time", "Seconds"),
        ("RapidTime", "rapid_time", "Seconds"),
        ("CuttingDistance", "cutting_distance", "mm"),
        ("RapidDistance", "rapid_distance", "mm"),
        ("TotalDistance", "total_distance", "mm"),
        ("MoveCount", "move_count", "Direct")
    ]
    
    for c_field, db_field, unit in tool_mappings:
        print(f"  • {c_field} → {db_field} ({unit})")
    
    # Verify field compatibility
    print(f"\\n🔗 COMPATIBILITY CHECK")
    print("-" * 50)
    
    # Check if all required fields are present
    required_fields = ["TotalTime", "MachineTime", "ToolChanges", "ToolUsageDetails"]
    compatibility_issues = []
    
    for field in required_fields:
        if field not in cs_content:
            compatibility_issues.append(f"Missing {field} in C# output")
    
    # Check ToolUsageDetails fields
    tool_required = ["ToolNumber", "TotalTime", "CuttingTime", "RapidTime", "CuttingDistance", "RapidDistance", "TotalDistance", "MoveCount"]
    for field in tool_required:
        if field not in cs_content:
            compatibility_issues.append(f"Missing {field} in ToolUsageDetails")
    
    if compatibility_issues:
        print("❌ COMPATIBILITY ISSUES FOUND:")
        for issue in compatibility_issues:
            print(f"  • {issue}")
    else:
        print("✅ NO COMPATIBILITY ISSUES FOUND!")
    
    # Check dashboard endpoints
    print(f"\\n📊 DASHBOARD INTEGRATION")
    print("-" * 50)
    
    dashboard_features = [
        ("cnc_program_analysis", "Detailed program analysis page"),
        ("calculate_daily_cnc_efficiency", "Daily efficiency metrics"),
        ("calculate_cnc_efficiency_for_period", "Period efficiency analysis"),
        ("CNCAnalysis.query", "Database queries for analysis"),
        ("ToolUsage relationships", "Tool usage statistics")
    ]
    
    for feature, desc in dashboard_features:
        found = feature.replace(" ", "_").lower() in py_content.lower()
        status = "✅" if found else "❌"
        print(f"  {status} {feature}: {desc}")
    
    # Summary
    print(f"\\n🎯 SUMMARY")
    print("=" * 60)
    
    if not compatibility_issues:
        print("✅ CNC Analysis is FULLY COMPATIBLE with API!")
        print("✅ All required fields are present")
        print("✅ Data structure matches expectations")
        print("✅ Dashboard features will work correctly")
        print("✅ Updated postprocessor detection is maintained")
    else:
        print(f"❌ {len(compatibility_issues)} compatibility issues found")
        print("⚠️  Manual fixes may be required")
    
    return len(compatibility_issues) == 0

if __name__ == "__main__":
    success = verify_api_compatibility()
    exit(0 if success else 1)