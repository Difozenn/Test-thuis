#!/usr/bin/env python3
"""
ULTIMATE COUNT2 FIX - USING ALL BRAINPOWER
Try EVERY possible method to extract ALL ACCURA items
"""

import pdfplumber
import re
import pandas as pd

pdf_path = "S04479_RAPPORT_Rudi Matterne_0411_MO07202-7203_TV-wand (7-7).PDF"

print("🧠 ULTIMATE COUNT2 EXTRACTION - ALL BRAINPOWER ACTIVATED")
print("=" * 60)

def method_1_all_pages_text():
    """Method 1: Text extraction from ALL pages, not just NESTING/OPDEELZAAG"""
    print("\n🔍 METHOD 1: All pages text extraction")
    count = 0
    items = []
    
    with pdfplumber.open(pdf_path) as pdf:
        all_text = ""
        for page in pdf.pages:
            if page.extract_text():
                all_text += page.extract_text() + "\n"
        
        lines = all_text.split('\n')
        
        # Process ALL numbered items, not just in specific sections
        for line in lines:
            if re.match(r'^\s*\d+\s+\w+', line) and 'mm' in line:
                mm_count = len(re.findall(r'\d+mm', line))
                if mm_count >= 2:
                    count += 1
                    items.append(line.strip())
    
    print(f"Found: {count} items")
    return count, items

def method_2_all_pages_tables():
    """Method 2: Table extraction from ALL pages"""
    print("\n🔍 METHOD 2: All pages table extraction")
    count = 0
    items = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row and len(row) > 0:
                        row_text = ' '.join([str(cell) if cell else '' for cell in row])
                        if re.match(r'^\s*\d+\s+\w+', row_text) and 'mm' in row_text:
                            mm_count = len(re.findall(r'\d+mm', row_text))
                            if mm_count >= 2:
                                count += 1
                                items.append(f"Page {page_num+1}: {row_text.strip()}")
    
    print(f"Found: {count} items")
    return count, items

def method_3_hybrid_text_table():
    """Method 3: Hybrid - both text AND table extraction"""
    print("\n🔍 METHOD 3: Hybrid text + table extraction")
    count = 0
    items = []
    found_items = set()  # Avoid duplicates
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            # Text extraction
            text = page.extract_text()
            if text:
                lines = text.split('\n')
                for line in lines:
                    if re.match(r'^\s*\d+\s+\w+', line) and 'mm' in line:
                        mm_count = len(re.findall(r'\d+mm', line))
                        if mm_count >= 2:
                            item_key = re.match(r'^\s*(\d+)\s+(\w+)', line)
                            if item_key:
                                key = f"{item_key.group(1)}_{item_key.group(2)}"
                                if key not in found_items:
                                    found_items.add(key)
                                    count += 1
                                    items.append(f"TEXT Page {page_num+1}: {line.strip()}")
            
            # Table extraction
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row and len(row) > 0:
                        row_text = ' '.join([str(cell) if cell else '' for cell in row])
                        if re.match(r'^\s*\d+\s+\w+', row_text) and 'mm' in row_text:
                            mm_count = len(re.findall(r'\d+mm', row_text))
                            if mm_count >= 2:
                                item_key = re.match(r'^\s*(\d+)\s+(\w+)', row_text)
                                if item_key:
                                    key = f"{item_key.group(1)}_{item_key.group(2)}"
                                    if key not in found_items:
                                        found_items.add(key)
                                        count += 1
                                        items.append(f"TABLE Page {page_num+1}: {row_text.strip()}")
    
    print(f"Found: {count} items")
    return count, items

def method_4_word_level():
    """Method 4: Word-level extraction with intelligent reconstruction"""
    print("\n🔍 METHOD 4: Word-level intelligent reconstruction")
    count = 0
    items = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            words = page.extract_words()
            
            # Group words by Y position (same line)
            lines_dict = {}
            for word in words:
                y_pos = round(word['top'], 1)  # Round to nearest 0.1
                if y_pos not in lines_dict:
                    lines_dict[y_pos] = []
                lines_dict[y_pos].append(word)
            
            # Sort words by X position within each line
            for y_pos in lines_dict:
                lines_dict[y_pos].sort(key=lambda w: w['x0'])
            
            # Reconstruct lines and check for edge processing
            for y_pos in sorted(lines_dict.keys()):
                line_words = [w['text'] for w in lines_dict[y_pos]]
                line_text = ' '.join(line_words)
                
                if re.match(r'^\s*\d+\s+\w+', line_text) and 'mm' in line_text:
                    mm_count = len(re.findall(r'\d+mm', line_text))
                    if mm_count >= 2:
                        count += 1
                        items.append(f"WORD Page {page_num+1}: {line_text.strip()}")
    
    print(f"Found: {count} items")
    return count, items

def method_5_character_level():
    """Method 5: Character-level with custom tolerance"""
    print("\n🔍 METHOD 5: Character-level custom tolerance")
    count = 0
    items = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            # Try different tolerance settings
            for x_tol in [0.5, 1, 2, 3]:
                for y_tol in [0.5, 1, 2, 3]:
                    try:
                        text = page.extract_text(x_tolerance=x_tol, y_tolerance=y_tol)
                        if text:
                            lines = text.split('\n')
                            page_count = 0
                            for line in lines:
                                if re.match(r'^\s*\d+\s+\w+', line) and 'mm' in line:
                                    mm_count = len(re.findall(r'\d+mm', line))
                                    if mm_count >= 2:
                                        page_count += 1
                            
                            if page_count > count:  # Take the best result
                                count = page_count
                                items = [f"CHAR Page {page_num+1} (x_tol={x_tol}, y_tol={y_tol}): {line.strip()}" 
                                        for line in lines 
                                        if re.match(r'^\s*\d+\s+\w+', line) and 'mm' in line and len(re.findall(r'\d+mm', line)) >= 2]
                    except:
                        continue
                        
            break  # Only test first page for tolerance optimization
    
    print(f"Found: {count} items (from optimization test)")
    return count, items

def method_6_bbox_scanning():
    """Method 6: Scan specific bounding box areas for tables"""
    print("\n🔍 METHOD 6: Bounding box table scanning")
    count = 0
    items = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            # Try different bounding box areas
            width = page.width
            height = page.height
            
            bboxes = [
                (0, 0, width, height),  # Full page
                (50, 100, width-50, height-100),  # Margins
                (30, 80, width-30, height-80),   # Smaller margins
                (0, 50, width, height-50),       # Skip header/footer
            ]
            
            for bbox in bboxes:
                try:
                    cropped = page.crop(bbox)
                    
                    # Try both text and table extraction on cropped area
                    text = cropped.extract_text()
                    if text:
                        lines = text.split('\n')
                        for line in lines:
                            if re.match(r'^\s*\d+\s+\w+', line) and 'mm' in line:
                                mm_count = len(re.findall(r'\d+mm', line))
                                if mm_count >= 2:
                                    count += 1
                                    items.append(f"BBOX Page {page_num+1}: {line.strip()}")
                    
                    tables = cropped.extract_tables()
                    for table in tables:
                        for row in table:
                            if row and len(row) > 0:
                                row_text = ' '.join([str(cell) if cell else '' for cell in row])
                                if re.match(r'^\s*\d+\s+\w+', row_text) and 'mm' in row_text:
                                    mm_count = len(re.findall(r'\d+mm', row_text))
                                    if mm_count >= 2:
                                        count += 1
                                        items.append(f"BBOX-TABLE Page {page_num+1}: {row_text.strip()}")
                except:
                    continue
                    
                break  # Use first successful bbox
    
    print(f"Found: {count} items")
    return count, items

def method_7_pattern_variations():
    """Method 7: Try different mm pattern variations"""
    print("\n🔍 METHOD 7: Pattern variations for edge processing")
    count = 0
    items = []
    
    # Different patterns that might indicate edge processing
    patterns = [
        r'\d+mm.*\d+mm',           # Standard: 19mm...1mm
        r'\d+\s+\d+\s+\d+\s+\d+',  # Numbers only: 19 1 1 2
        r'L\d|B\d|R\d',            # L1, B2, etc.
        r'Fineer.*Fineer',         # Multiple fineer mentions
        r'\d+mm[^0-9]*\d+mm',      # mm values separated by text
    ]
    
    with pdfplumber.open(pdf_path) as pdf:
        all_text = ""
        for page in pdf.pages:
            if page.extract_text():
                all_text += page.extract_text() + "\n"
        
        lines = all_text.split('\n')
        found_items = set()
        
        for line in lines:
            if re.match(r'^\s*\d+\s+\w+', line):
                # Check against all patterns
                edge_processing_found = False
                
                for pattern in patterns:
                    if re.search(pattern, line):
                        edge_processing_found = True
                        break
                
                if edge_processing_found:
                    item_key = re.match(r'^\s*(\d+)\s+(\w+)', line)
                    if item_key:
                        key = f"{item_key.group(1)}_{item_key.group(2)}"
                        if key not in found_items:
                            found_items.add(key)
                            count += 1
                            items.append(f"PATTERN: {line.strip()}")
    
    print(f"Found: {count} items")
    return count, items

# Test all methods
print("🚀 TESTING ALL METHODS...")

results = {}
results['method_1'] = method_1_all_pages_text()
results['method_2'] = method_2_all_pages_tables()
results['method_3'] = method_3_hybrid_text_table()
results['method_4'] = method_4_word_level()
results['method_5'] = method_5_character_level()
results['method_6'] = method_6_bbox_scanning()
results['method_7'] = method_7_pattern_variations()

print(f"\n🏆 ULTIMATE RESULTS:")
print("=" * 40)
for method, (count, items) in results.items():
    print(f"{method}: {count} items")

best_method = max(results, key=lambda x: results[x][0])
best_count, best_items = results[best_method]

print(f"\n🎯 WINNER: {best_method} with {best_count} items!")
print(f"Target: ~84 items")
print(f"Achievement: {best_count/84*100:.1f}% of target")

# Save the best results
pd.DataFrame(best_items[:20], columns=["Items"]).to_excel("ultimate_count2_results.xlsx", index=False)
print(f"\n✅ Best results saved to ultimate_count2_results.xlsx")