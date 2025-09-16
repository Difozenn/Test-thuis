#!/usr/bin/env python3
"""Test script to verify the search functionality works correctly"""

import sqlite3
import os
from datetime import datetime

# Mock function to simulate the search logic
def test_search_projects(search_query="", sort_by="recent"):
    """Test the search and sort functionality"""
    
    # Connect to database
    db_path = 'project_datalog.db'
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get all unique projects
    c.execute("""
        SELECT DISTINCT project
        FROM logs
        WHERE project IS NOT NULL AND project != ''
        ORDER BY project
    """)
    
    all_projects = [row['project'] for row in c.fetchall()]
    print(f"Total projects in database: {len(all_projects)}")
    
    projects = []
    
    for project_code in all_projects[:10]:  # Test with first 10 projects
        # Get metadata
        c.execute("""
            SELECT mo_number, so_number, customer_name, color, MAX(timestamp) as latest_timestamp
            FROM logs
            WHERE project = ?
            GROUP BY project
        """, (project_code,))
        
        result = c.fetchone()
        if result:
            project_dict = {
                'code': project_code,
                'mo_number': result['mo_number'] or '',
                'so_number': result['so_number'] or '',
                'customer_name': result['customer_name'] or '',
                'color': result['color'] or '',
                'timestamp': result['latest_timestamp']
            }
            projects.append(project_dict)
    
    print(f"\nBefore filtering: {len(projects)} projects")
    
    # Apply search filter if provided
    if search_query:
        search_lower = search_query.lower()
        filtered_projects = []
        for proj in projects:
            # Search in multiple fields
            searchable_text = (
                (proj['code'] or '').lower() + ' ' +
                (proj['mo_number'] or '').lower() + ' ' +
                (proj['so_number'] or '').lower() + ' ' +
                (proj['customer_name'] or '').lower() + ' ' +
                (proj['color'] or '').lower()
            )
            if search_lower in searchable_text:
                filtered_projects.append(proj)
        projects = filtered_projects
        print(f"After search filter '{search_query}': {len(projects)} projects")
    
    # Apply sorting
    if sort_by == 'recent':
        projects.sort(key=lambda x: x['timestamp'] or '', reverse=True)
        print(f"Sorted by: most recent first")
    elif sort_by == 'oldest':
        projects.sort(key=lambda x: x['timestamp'] or '')
        print(f"Sorted by: oldest first")
    elif sort_by == 'code':
        projects.sort(key=lambda x: x['code'])
        print(f"Sorted by: project code")
    elif sort_by == 'customer':
        projects.sort(key=lambda x: (x['customer_name'] or 'zzz', x['code']))
        print(f"Sorted by: customer name")
    
    # Display results
    print(f"\nResults (showing first 5):")
    for i, proj in enumerate(projects[:5], 1):
        print(f"{i}. {proj['code']} - Customer: {proj['customer_name'] or 'N/A'} - Timestamp: {proj['timestamp']}")
    
    conn.close()
    return projects

# Test different scenarios
print("="*60)
print("Test 1: No search, recent sort")
print("="*60)
test_search_projects()

print("\n" + "="*60)
print("Test 2: Search for 'MO06', sorted by code")
print("="*60)
test_search_projects(search_query="MO06", sort_by="code")

print("\n" + "="*60)
print("Test 3: Search for customer name (if any)")
print("="*60)
test_search_projects(search_query="Frank", sort_by="customer")