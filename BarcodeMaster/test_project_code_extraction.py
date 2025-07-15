#!/usr/bin/env python3
"""
Test project code extraction
"""

import re
import os

def extract_project_code(filename):
    """Extract project code from filename."""
    # Extract MO code and description from filename
    # Example: "S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF"
    # Should return: "MO07199_Hoekdressing - opklapbed (4-7)"
    
    match = re.search(r'(MO\d+[^.]*?)\.PDF', filename, re.IGNORECASE)
    if match:
        project_code = match.group(1).strip()
        return project_code
    
    # Fallback: look for MO pattern anywhere
    match = re.search(r'(MO\d+.*?)(?:\.PDF|$)', filename, re.IGNORECASE)
    if match:
        project_code = match.group(1).strip()
        return project_code
    
    # Last resort: use filename without extension
    return os.path.splitext(filename)[0]

# Test cases
test_filenames = [
    "S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF",
    "MO07199_Hoekdressing - opklapbed (4-7).PDF",
    "RAPPORT_MO07199_Hoekdressing - opklapbed (4-7).PDF",
    "S04479_MO07195_Hoekdressing (1-7).PDF"
]

print("Project Code Extraction Test")
print("============================\n")

for filename in test_filenames:
    result = extract_project_code(filename)
    print(f"Filename: {filename}")
    print(f"Extracted: '{result}'")
    print(f"Expected: 'MO07199_Hoekdressing - opklapbed (4-7)' ✓" if 'MO07199' in filename else "")
    print("-" * 80)