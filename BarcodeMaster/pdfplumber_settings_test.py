#!/usr/bin/env python3
"""
TEST DIFFERENT PDFPLUMBER SETTINGS
Try various extraction methods to capture L1/L2/B1/B2 edge processing data
"""

import pdfplumber
import re
import pandas as pd

pdf_path = "S04479_RAPPORT_Rudi Matterne_0411_MO07202-7203_TV-wand (7-7).PDF"

print("🔧 TESTING DIFFERENT PDFPLUMBER SETTINGS")
print("=" * 50)

def test_method_1_default():
    """Default text extraction"""
    print("\n📊 METHOD 1: Default extract_text()")
    count = 0
    samples = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            if page_num > 5:  # Test first few pages only
                break
            text = page.extract_text()
            if text:
                lines = text.split('\n')
                for line in lines:
                    if re.match(r'^\s*\d+\s+\w+', line) and 'mm' in line:
                        mm_count = len(re.findall(r'\d+mm', line))
                        if mm_count >= 2:
                            count += 1
                            if len(samples) < 3:
                                samples.append(f"  {line.strip()}")
    
    print(f"Count: {count}")
    for sample in samples:
        print(sample)
    return count

def test_method_2_layout():
    """Layout-preserving extraction"""
    print("\n📊 METHOD 2: extract_text(layout=True)")
    count = 0
    samples = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            if page_num > 5:
                break
            text = page.extract_text(layout=True)
            if text:
                lines = text.split('\n')
                for line in lines:
                    if re.match(r'^\s*\d+\s+\w+', line) and 'mm' in line:
                        mm_count = len(re.findall(r'\d+mm', line))
                        if mm_count >= 2:
                            count += 1
                            if len(samples) < 3:
                                samples.append(f"  {line.strip()}")
    
    print(f"Count: {count}")
    for sample in samples:
        print(sample)
    return count

def test_method_3_table_extract():
    """Table extraction"""
    print("\n📊 METHOD 3: extract_tables()")
    count = 0
    samples = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            if page_num > 5:
                break
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row and len(row) > 0:
                        row_text = ' '.join([str(cell) if cell else '' for cell in row])
                        if re.match(r'^\s*\d+\s+\w+', row_text) and 'mm' in row_text:
                            mm_count = len(re.findall(r'\d+mm', row_text))
                            if mm_count >= 2:
                                count += 1
                                if len(samples) < 3:
                                    samples.append(f"  {row_text.strip()}")
    
    print(f"Count: {count}")
    for sample in samples:
        print(sample)
    return count

def test_method_4_words():
    """Word-level extraction with positioning"""
    print("\n📊 METHOD 4: extract_words() with positioning")
    count = 0
    samples = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            if page_num > 5:
                break
            words = page.extract_words()
            
            # Group words by approximate Y position (same line)
            lines_dict = {}
            for word in words:
                y_pos = round(word['top'])
                if y_pos not in lines_dict:
                    lines_dict[y_pos] = []
                lines_dict[y_pos].append(word['text'])
            
            # Reconstruct lines and check for edge processing
            for y_pos in sorted(lines_dict.keys()):
                line_text = ' '.join(lines_dict[y_pos])
                if re.match(r'^\s*\d+\s+\w+', line_text) and 'mm' in line_text:
                    mm_count = len(re.findall(r'\d+mm', line_text))
                    if mm_count >= 2:
                        count += 1
                        if len(samples) < 3:
                            samples.append(f"  {line_text.strip()}")
    
    print(f"Count: {count}")
    for sample in samples:
        print(sample)
    return count

def test_method_5_chars():
    """Character-level extraction"""
    print("\n📊 METHOD 5: extract_text(x_tolerance=1, y_tolerance=1)")
    count = 0
    samples = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            if page_num > 5:
                break
            text = page.extract_text(x_tolerance=1, y_tolerance=1)
            if text:
                lines = text.split('\n')
                for line in lines:
                    if re.match(r'^\s*\d+\s+\w+', line) and 'mm' in line:
                        mm_count = len(re.findall(r'\d+mm', line))
                        if mm_count >= 2:
                            count += 1
                            if len(samples) < 3:
                                samples.append(f"  {line.strip()}")
    
    print(f"Count: {count}")
    for sample in samples:
        print(sample)
    return count

def test_method_6_crop():
    """Crop specific table areas"""
    print("\n📊 METHOD 6: Crop table areas")
    count = 0
    samples = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            if page_num > 5:
                break
            
            # Try to find and crop table areas
            bbox = (50, 100, page.width - 50, page.height - 100)  # Rough table area
            cropped = page.crop(bbox)
            text = cropped.extract_text()
            
            if text:
                lines = text.split('\n')
                for line in lines:
                    if re.match(r'^\s*\d+\s+\w+', line) and 'mm' in line:
                        mm_count = len(re.findall(r'\d+mm', line))
                        if mm_count >= 2:
                            count += 1
                            if len(samples) < 3:
                                samples.append(f"  {line.strip()}")
    
    print(f"Count: {count}")
    for sample in samples:
        print(sample)
    return count

# Test all methods
results = {}
results['method_1'] = test_method_1_default()
results['method_2'] = test_method_2_layout()
results['method_3'] = test_method_3_table_extract()
results['method_4'] = test_method_4_words()
results['method_5'] = test_method_5_chars()
results['method_6'] = test_method_6_crop()

print(f"\n🏆 RESULTS SUMMARY:")
print("=" * 30)
for method, count in results.items():
    print(f"{method}: {count} items")

best_method = max(results, key=results.get)
print(f"\n✅ BEST METHOD: {best_method} with {results[best_method]} items")