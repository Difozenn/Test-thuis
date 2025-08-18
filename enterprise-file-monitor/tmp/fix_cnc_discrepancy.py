#!/usr/bin/env python3
"""
Fix CNC analysis time discrepancy
The issue: Tool sessions are storing time in MINUTES but being treated as SECONDS in the web display
"""

import sys

def analyze_problem():
    """
    PROBLEM IDENTIFIED:
    
    1. C# TCALCAnalyzer stores tool session times in MINUTES:
       - Line 827: public double TotalTime => CuttingTime + RapidTime;
       - CuttingTime and RapidTime are accumulated in MINUTES
    
    2. C# sends to Python:
       - Line 4297: TotalTime = Math.Round(session.TotalTime * 60, 2)
       - Converts minutes to seconds before sending
    
    3. Python stores in database:
       - Line 1972: total_time=tool_detail.get('TotalTime', 0.0)  # seconds
       - Stores as seconds correctly
    
    4. Python displays in template:
       - Line 2756: 'duration_seconds': tool.total_time or 20
       - Sends to template as seconds
    
    5. Template displays:
       - Line 345: format_seconds_human(tool.duration_seconds)
       - Should display correctly
    
    ACTUAL ISSUE:
    The web shows 6 tools including duplicates (T601 and T181 appear twice).
    This suggests old tool usage records are not being deleted when:
    1. A file is re-analyzed
    2. An event is deleted
    
    The 15:58 (958 seconds) is likely the sum of:
    - Current analysis tools
    - Orphaned tools from previous analyses
    """
    
    print("""
    ISSUE ANALYSIS:
    ===============
    
    Expected (TCALC_HH7 output for nesting.NC):
    - Total time: 39.5 seconds
    - Processing time: 10.3 seconds
    - Tool change time: 26.1 seconds (2 changes × 13.05s)
    - Rapids: 3.2 seconds
    
    Web Display Shows:
    - 6 tools (including duplicates T601 and T181)
    - Total time: 15:58 (958 seconds)
    
    ROOT CAUSE:
    -----------
    Tool usage records from previous analyses are not being deleted.
    When the same file is analyzed again, new tool records are added
    but old ones remain, causing:
    1. Duplicate tool entries
    2. Incorrect time summation
    
    SOLUTION:
    ---------
    1. Before creating new CNC analysis, delete any existing analysis for the same file
    2. Ensure cascade deletion properly removes all tool_usage records
    3. Add unique constraint to prevent duplicate tools in same analysis
    """)

def generate_fix():
    """Generate the code fix"""
    
    print("""
    
    CODE FIX for app.py:
    ====================
    
    In the log_event endpoint (around line 1920), before creating new CNC analysis:
    
    # Delete any existing CNC analysis for this file to prevent duplicates
    existing_analysis = CNCAnalysis.query.filter_by(
        file_path=cnc_analysis_data.get('Filename', file_path)
    ).first()
    
    if existing_analysis:
        # Delete all tool usage for this analysis
        ToolUsage.query.filter_by(cnc_analysis_id=existing_analysis.id).delete()
        # Delete the analysis itself
        db.session.delete(existing_analysis)
        db.session.flush()  # Ensure deletion happens before creating new records
        print(f"[DEBUG] Deleted existing CNC analysis ID {existing_analysis.id} for {file_path}")
    
    
    Alternative approach - Add to CNCAnalysis model (around line 949):
    
    @staticmethod
    def create_or_update(event_id, file_path, cycle_time_seconds, machine_time_minutes, tool_changes):
        # Check if analysis already exists for this event
        existing = CNCAnalysis.query.filter_by(event_id=event_id).first()
        
        if existing:
            # Update existing
            existing.cycle_time_seconds = cycle_time_seconds
            existing.machine_time_minutes = machine_time_minutes
            existing.tool_changes = tool_changes
            # Delete old tool usage records
            ToolUsage.query.filter_by(cnc_analysis_id=existing.id).delete()
            return existing
        else:
            # Create new
            return CNCAnalysis(
                event_id=event_id,
                file_path=file_path,
                cycle_time_seconds=cycle_time_seconds,
                machine_time_minutes=machine_time_minutes,
                tool_changes=tool_changes
            )
    """)

if __name__ == "__main__":
    analyze_problem()
    generate_fix()