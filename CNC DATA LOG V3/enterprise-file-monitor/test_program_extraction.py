#!/usr/bin/env python3
"""
Test script to verify CNC program name extraction from .nc files
"""
import os
import tempfile
import re

def extract_program_name_from_cnc_file(file_path):
    """Extract .HOPS/.HOP program name from CNC file content"""
    try:
        if not file_path or not os.path.exists(file_path):
            return None
            
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Look for .HOPS or .HOP file references
        
        # Pattern to match .HOPS or .HOP files
        hop_pattern = r'([A-Za-z0-9_-]+\.HOP[S]?)'
        matches = re.findall(hop_pattern, content, re.IGNORECASE)
        
        if matches:
            # Return the first .HOP/.HOPS file found
            return matches[0]
        
        # If no .HOP/.HOPS found, try to find program name in comments
        # Look for common CNC program name patterns
        program_patterns = [
            r'PROGRAM\s*[:=]\s*([A-Za-z0-9_-]+)',
            r'PROGRAM\s+([A-Za-z0-9_-]+)',
            r';\s*PROGRAM\s*[:=]\s*([A-Za-z0-9_-]+)',
            r';\s*([A-Za-z0-9_-]+\.HOP[S]?)',
            r'\(([A-Za-z0-9_-]+\.HOP[S]?)\)'
        ]
        
        for pattern in program_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                return matches[0]
        
        return None
        
    except Exception as e:
        print(f"Error extracting program name from {file_path}: {e}")
        return None

def test_program_extraction():
    """Test the program name extraction function"""
    
    # Test cases with different CNC file formats
    test_cases = [
        {
            'name': 'Direct .HOPS reference',
            'content': '''
G90 G54 G21 G40 G49 G80
M06 T1
S12000 M03
; Program: Field1.HOPS
G00 X0 Y0 Z5
G01 Z-2 F1000
''',
            'expected': 'Field1.HOPS'
        },
        {
            'name': 'Direct .HOP reference',
            'content': '''
G90 G54 G21 G40 G49 G80
M06 T1
S12000 M03
; Program: Panel_A.HOP
G00 X0 Y0 Z5
G01 Z-2 F1000
''',
            'expected': 'Panel_A.HOP'
        },
        {
            'name': 'Multiple .HOPS references',
            'content': '''
G90 G54 G21 G40 G49 G80
; First program: Part1.HOPS
M06 T1
S12000 M03
; Second program: Part2.HOPS
G00 X0 Y0 Z5
''',
            'expected': 'Part1.HOPS'  # Should return first match
        },
        {
            'name': 'PROGRAM = format',
            'content': '''
G90 G54 G21 G40 G49 G80
; PROGRAM = DoorFrame_V2
M06 T1
S12000 M03
G00 X0 Y0 Z5
''',
            'expected': 'DoorFrame_V2'
        },
        {
            'name': 'PROGRAM: format',
            'content': '''
G90 G54 G21 G40 G49 G80
; PROGRAM: Cabinet_Side
M06 T1
S12000 M03
G00 X0 Y0 Z5
''',
            'expected': 'Cabinet_Side'
        },
        {
            'name': 'Parentheses format',
            'content': '''
G90 G54 G21 G40 G49 G80
M06 T1
S12000 M03
(WorkBench_Top.HOP)
G00 X0 Y0 Z5
''',
            'expected': 'WorkBench_Top.HOP'
        },
        {
            'name': 'No program name found',
            'content': '''
G90 G54 G21 G40 G49 G80
M06 T1
S12000 M03
G00 X0 Y0 Z5
G01 Z-2 F1000
''',
            'expected': None
        }
    ]
    
    print("🔍 Testing CNC Program Name Extraction")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test_case['name']}")
        
        # Create temporary file with test content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.nc', delete=False) as f:
            f.write(test_case['content'])
            temp_file = f.name
        
        try:
            # Extract program name
            result = extract_program_name_from_cnc_file(temp_file)
            
            # Check result
            if result == test_case['expected']:
                print(f"✅ PASS: Expected '{test_case['expected']}', got '{result}'")
            else:
                print(f"❌ FAIL: Expected '{test_case['expected']}', got '{result}'")
                
        finally:
            # Clean up temp file
            os.unlink(temp_file)
    
    print(f"\n" + "=" * 50)
    print("🎯 Test Summary:")
    print("Program name extraction will now show .HOPS/.HOP files")
    print("instead of the monitored .nc file path in the dashboard.")

if __name__ == "__main__":
    test_program_extraction()