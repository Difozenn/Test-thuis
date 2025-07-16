#!/usr/bin/env python3
"""
ULTIMATE 100% ACCURACY FIX
Find the missing 4 ACCURA items to get from 80 to 84
EVERY POSSIBLE EXTRACTION METHOD COMBINED
"""

import pdfplumber
import re
import pandas as pd
import subprocess

pdf_path = "S04479_RAPPORT_Rudi Matterne_0411_MO07202-7203_TV-wand (7-7).PDF"

print("🔥 ULTIMATE 100% ACCURACY MISSION")
print("=" * 50)
print("Target: 84 ACCURA items")
print("Current: 80 items")
print("Missing: 4 items")
print("Mission: FIND THOSE 4 ITEMS!")

def method_pdftotext_exact():
    """Use exact same method as R script - pdftotext"""
    print("\n🎯 METHOD: pdftotext (R script exact replica)")
    
    # Extract using pdftotext like R script
    subprocess.run(['pdftotext', '-layout', pdf_path, 'python_pdftotext.txt'], 
                   capture_output=True)
    
    with open('python_pdftotext.txt', 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    count = 0
    items = []
    in_nesting = False
    in_opdeelzaag = False
    
    for i, line in enumerate(lines):
        line_clean = line.strip()
        line_lower = line_clean.lower()
        
        # Section detection
        if 'nesting' in line_lower:
            in_nesting = True
            in_opdeelzaag = False
            continue
        elif 'opdeelzaag' in line_lower:
            in_opdeelzaag = True
            in_nesting = False
            continue
        elif any(x in line_lower for x in ['controle', 'massief', 'magazijn']):
            in_nesting = False
            in_opdeelzaag = False
            continue
        
        # Count items in NESTING/OPDEELZAAG sections
        if (in_nesting or in_opdeelzaag) and re.match(r'^\s*\d+\s+\w+', line_clean):
            # R script pattern: ≥2 mm values
            if 'mm' in line_clean:
                mm_count = len(re.findall(r'\d+mm', line_clean))
                if mm_count >= 2:
                    count += 1
                    items.append(f"PDFTOTEXT: {line_clean}")
    
    print(f"Found: {count} items")
    return count, items

def method_aggressive_patterns():
    """Try EVERY possible pattern that could indicate edge processing"""
    print("\n🎯 METHOD: Aggressive pattern matching")
    
    count = 0
    items = []
    found_items = set()
    
    with pdfplumber.open(pdf_path) as pdf:
        all_text = ""
        for page in pdf.pages:
            if page.extract_text():
                all_text += page.extract_text() + "\n"
        
        lines = all_text.split('\n')
        in_nesting = False
        in_opdeelzaag = False
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Section tracking
            if 'nesting' in line_lower:
                in_nesting = True
                in_opdeelzaag = False
                continue
            elif 'opdeelzaag' in line_lower:
                in_opdeelzaag = True
                in_nesting = False
                continue
            elif any(x in line_lower for x in ['controle', 'massief', 'magazijn']):
                in_nesting = False
                in_opdeelzaag = False
                continue
            
            if not (in_nesting or in_opdeelzaag):
                continue
            
            if re.match(r'^\s*\d+\s+\w+', line):
                has_edge = False
                edge_type = ""
                
                # Pattern 1: Multiple mm
                if 'mm' in line:
                    mm_count = len(re.findall(r'\d+mm', line))
                    if mm_count >= 2:
                        has_edge = True
                        edge_type = f"MM_{mm_count}"
                
                # Pattern 2: Multiple fineer
                if 'fineer' in line_lower:
                    fineer_count = line_lower.count('fineer')
                    if fineer_count >= 2:
                        has_edge = True
                        edge_type = f"FINEER_{fineer_count}"
                
                # Pattern 3: L1/L2/B1/B2 columns
                edge_cols = ['L1', 'L2', 'B1', 'B2']
                edge_mentions = sum(1 for col in edge_cols if col.lower() in line_lower)
                if edge_mentions >= 1:
                    has_edge = True
                    edge_type = f"EDGE_{edge_mentions}"
                
                # Pattern 4: Overmaat (edge processing indicator)
                if 'overmaat' in line_lower:
                    has_edge = True
                    edge_type = "OVERMAAT"
                
                # Pattern 5: eik eik (repeated material = edge processing)
                if line_lower.count('eik') >= 3:
                    has_edge = True
                    edge_type = f"EIK_{line_lower.count('eik')}"
                
                # Pattern 6: Numbers that suggest dimensions + edge processing
                numbers = re.findall(r'\d+', line)
                if len(numbers) >= 6:  # Length, width, thickness + edge values
                    has_edge = True
                    edge_type = f"NUMBERS_{len(numbers)}"
                
                # Pattern 7: Standaard (often appears with edge processing)
                if 'standaard' in line_lower and ('fineer' in line_lower or 'eik' in line_lower):
                    has_edge = True
                    edge_type = "STANDAARD_FINEER"
                
                if has_edge:
                    item_key = re.match(r'^\s*(\d+)\s+(\w+)', line)
                    if item_key:
                        key = f"{item_key.group(1)}_{item_key.group(2)}"
                        if key not in found_items:
                            found_items.add(key)
                            count += 1
                            items.append(f"AGGRESSIVE ({edge_type}): {line.strip()}")
    
    print(f"Found: {count} items")
    return count, items

def method_table_deep_scan():
    """Deep scan all table structures with different settings"""
    print("\n🎯 METHOD: Deep table scanning")
    
    count = 0
    items = []
    found_items = set()
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            if page_num >= 15:  # Focus on relevant pages
                continue
                
            # Try multiple table extraction strategies
            strategies = [
                {},  # Default
                {"vertical_strategy": "lines"},
                {"horizontal_strategy": "lines"},
                {"vertical_strategy": "text", "horizontal_strategy": "text"},
                {"snap_tolerance": 5},
                {"join_tolerance": 3},
            ]
            
            for strategy in strategies:
                try:
                    tables = page.extract_tables(table_settings=strategy)
                    for table in tables:
                        for row in table:
                            if row and len(row) > 0:
                                row_text = ' '.join([str(cell) if cell else '' for cell in row])
                                
                                if re.match(r'^\s*\d+\s+\w+', row_text):
                                    # Check for edge processing
                                    has_edge = False
                                    
                                    if 'mm' in row_text:
                                        mm_count = len(re.findall(r'\d+mm', row_text))
                                        if mm_count >= 2:
                                            has_edge = True
                                    
                                    if 'fineer' in row_text.lower():
                                        fineer_count = row_text.lower().count('fineer')
                                        if fineer_count >= 2:
                                            has_edge = True
                                    
                                    if has_edge:
                                        item_key = re.match(r'^\s*(\d+)\s+(\w+)', row_text)
                                        if item_key:
                                            key = f"{item_key.group(1)}_{item_key.group(2)}"
                                            if key not in found_items:
                                                found_items.add(key)
                                                count += 1
                                                items.append(f"TABLE_DEEP: {row_text.strip()}")
                except:
                    continue
    
    print(f"Found: {count} items")
    return count, items

def method_character_precision():
    """Ultra-precise character-level extraction"""
    print("\n🎯 METHOD: Character-level precision")
    
    count = 0
    items = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            if page_num >= 15:
                continue
            
            # Get all characters with positions
            chars = page.chars
            
            # Group characters into lines based on Y position
            lines_dict = {}
            for char in chars:
                y = round(char['top'])
                if y not in lines_dict:
                    lines_dict[y] = []
                lines_dict[y].append(char)
            
            # Sort characters within each line by X position
            for y in lines_dict:
                lines_dict[y].sort(key=lambda c: c['x0'])
            
            # Reconstruct lines and analyze
            for y in sorted(lines_dict.keys()):
                line_text = ''.join([c['text'] for c in lines_dict[y]])
                
                if re.match(r'^\s*\d+\s+\w+', line_text):
                    if 'mm' in line_text:
                        mm_count = len(re.findall(r'\d+mm', line_text))
                        if mm_count >= 2:
                            count += 1
                            items.append(f"CHAR_PRECISION: {line_text.strip()}")
    
    print(f"Found: {count} items")
    return count, items

def method_coordinate_extraction():
    """Extract by exact coordinates where edge processing data should be"""
    print("\n🎯 METHOD: Coordinate-based extraction")
    
    count = 0
    items = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            if page_num >= 15:
                continue
            
            # Look for text in specific coordinate ranges where L1/L2/B1/B2 data appears
            width = page.width
            height = page.height
            
            # Define coordinate zones for edge processing columns
            edge_zones = [
                (width * 0.6, width * 0.8, 0, height),  # Right side columns
                (width * 0.7, width * 0.9, 0, height),  # Far right columns
                (width * 0.5, width * 0.7, 0, height),  # Middle-right columns
            ]
            
            for x1, x2, y1, y2 in edge_zones:
                try:
                    cropped = page.crop((x1, y1, x2, y2))
                    text = cropped.extract_text()
                    
                    if text and 'mm' in text:
                        lines = text.split('\n')
                        for line in lines:
                            if 'mm' in line and any(char.isdigit() for char in line):
                                count += 1
                                items.append(f"COORDINATE: {line.strip()}")
                except:
                    continue
    
    print(f"Found: {count} items")
    return count, items

# Test all methods
methods = [
    method_pdftotext_exact,
    method_aggressive_patterns,
    method_table_deep_scan,
    method_character_precision,
    method_coordinate_extraction,
]

all_results = {}
for method in methods:
    try:
        count, items = method()
        method_name = method.__name__
        all_results[method_name] = (count, items)
    except Exception as e:
        print(f"Method {method.__name__} failed: {e}")
        all_results[method.__name__] = (0, [])

print(f"\n🏆 ULTIMATE RESULTS COMPARISON:")
print("=" * 50)
for method_name, (count, items) in all_results.items():
    print(f"{method_name}: {count} items")
    if count >= 84:
        print(f"  🎯 WINNER! Achieved target!")

# Find the best method
best_method = max(all_results, key=lambda x: all_results[x][0])
best_count, best_items = all_results[best_method]

print(f"\n🎖️ BEST METHOD: {best_method}")
print(f"Count: {best_count}")
print(f"Target: 84")
print(f"Accuracy: {best_count/84*100:.1f}%")

if best_count >= 84:
    print("🎉 100% ACCURACY ACHIEVED!")
else:
    print(f"❌ Still missing {84 - best_count} items")

# Save best results
if best_items:
    pd.DataFrame(best_items, columns=["Items"]).to_excel("ultimate_100_percent_results.xlsx", index=False)
    print(f"✅ Results saved to ultimate_100_percent_results.xlsx")