#!/usr/bin/env python3
"""
Cleanup script to remove duplicate tool usage entries with incorrect times.
Keeps only the most recent/correct entries for each tool.
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import ToolUsage, CNCAnalysis, Event

# Database connection
DATABASE_URL = 'sqlite:///enterprise_monitor.db'
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

def cleanup_duplicates():
    """Remove duplicate tool usage entries, keeping the most accurate ones."""
    
    # Get all CNC analyses
    cnc_analyses = session.query(CNCAnalysis).all()
    
    total_removed = 0
    
    for analysis in cnc_analyses:
        tools = session.query(ToolUsage).filter_by(cnc_analysis_id=analysis.id).order_by(ToolUsage.id).all()
        
        if not tools:
            continue
            
        # Group tools by tool number
        tool_groups = {}
        for tool in tools:
            if tool.tool_number not in tool_groups:
                tool_groups[tool.tool_number] = []
            tool_groups[tool.tool_number].append(tool)
        
        # For each tool number, keep only the entry with reasonable times
        for tool_number, entries in tool_groups.items():
            if len(entries) <= 1:
                continue
                
            print(f"  CNC Analysis {analysis.id}, Tool T{tool_number}: {len(entries)} entries found")
            
            # Find the most reasonable entry (times < 100 seconds are more likely correct)
            best_entry = None
            for entry in entries:
                print(f"    Entry {entry.id}: total_time={entry.total_time:.1f}s, cutting={entry.cutting_time:.1f}s")
                
                # Prefer entries with reasonable times (< 100s) and non-zero values
                if entry.total_time > 0 and entry.total_time < 100:
                    if best_entry is None or entry.id > best_entry.id:  # Prefer newer entries
                        best_entry = entry
            
            # If no reasonable entry found, keep the newest one
            if best_entry is None:
                best_entry = entries[-1]
            
            # Remove all except the best entry
            for entry in entries:
                if entry.id != best_entry.id:
                    print(f"    Removing entry {entry.id} (keeping {best_entry.id} with {best_entry.total_time:.1f}s)")
                    session.delete(entry)
                    total_removed += 1
    
    # Commit changes
    if total_removed > 0:
        session.commit()
        print(f"\nRemoved {total_removed} duplicate tool usage entries")
    else:
        print("\nNo duplicate entries found")
    
    session.close()

def show_current_data():
    """Display current tool usage data for verification."""
    
    # Find the most recent CNC analysis
    recent_event = session.query(Event).filter(
        Event.event_type == 'cnc_analysis'
    ).order_by(Event.timestamp.desc()).first()
    
    if recent_event and recent_event.cnc_analysis:
        analysis = recent_event.cnc_analysis
        print(f"\nMost recent CNC analysis (Event {recent_event.id}):")
        print(f"  File: {os.path.basename(analysis.file_path)}")
        print(f"  Timestamp: {recent_event.timestamp}")
        print(f"  Tool usage:")
        
        tools = session.query(ToolUsage).filter_by(cnc_analysis_id=analysis.id).order_by(ToolUsage.tool_number).all()
        for tool in tools:
            print(f"    T{tool.tool_number}: total={tool.total_time:.1f}s, cutting={tool.cutting_time:.1f}s, "
                  f"distance={tool.total_distance:.1f}mm")

if __name__ == "__main__":
    print("Tool Usage Duplicate Cleanup")
    print("=" * 50)
    
    print("\nBefore cleanup:")
    show_current_data()
    
    print("\nCleaning up duplicates...")
    cleanup_duplicates()
    
    print("\nAfter cleanup:")
    show_current_data()