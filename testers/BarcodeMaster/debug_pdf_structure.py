#!/usr/bin/env python3
"""
Debug the actual PDF structure to understand why extraction is failing
"""

import pdfplumber
import json

def analyze_pdf_structure(pdf_path: str):
    """Deep dive into why this PDF is so hard to extract"""
    
    print("🔍 ANALYZING PDF STRUCTURE")
    print("="*50)
    
    with pdfplumber.open(pdf_path) as pdf:
        # Check a problematic page (e.g., page 13)
        page = pdf.pages[12]  # Page 13 (0-indexed)
        
        print(f"📄 Page 13 Analysis:")
        print(f"   Dimensions: {page.width} x {page.height}")
        
        # 1. Check if tables are actually embedded as tables
        tables = page.extract_tables()
        print(f"   Tables found by extract_tables(): {len(tables)}")
        
        if tables:
            for i, table in enumerate(tables):
                print(f"     Table {i}: {len(table)} rows x {len(table[0]) if table else 0} cols")
                if table:
                    print(f"       First row: {table[0][:5]}...")
        
        # 2. Check raw text extraction
        text = page.extract_text()
        lines = text.split('\n') if text else []
        print(f"   Raw text lines: {len(lines)}")
        
        # Show lines that contain item numbers
        item_lines = [line for line in lines if line.strip() and line.strip()[0].isdigit()]
        print(f"   Lines starting with numbers: {len(item_lines)}")
        if item_lines:
            print(f"   Example: {item_lines[0][:80]}...")
        
        # 3. Check character-level extraction
        chars = page.chars
        print(f"   Individual characters: {len(chars)}")
        
        # Group characters by Y position to see row structure
        y_positions = {}
        for char in chars:
            y = round(char['y0'])
            if y not in y_positions:
                y_positions[y] = []
            y_positions[y].append(char)
        
        print(f"   Distinct Y positions (rows): {len(y_positions)}")
        
        # 4. Check for actual table structure in PDF
        page_obj = page.page_obj
        print(f"   PDF page object type: {type(page_obj)}")
        
        # 5. Look for specific problematic patterns
        print(f"\n🔍 PROBLEM ANALYSIS:")
        
        # Check if text is positioned in a table-like structure
        if len(y_positions) > 0:
            # Sample a few rows
            sample_rows = sorted(y_positions.keys(), reverse=True)[:5]
            for y in sample_rows:
                row_chars = y_positions[y]
                row_text = ''.join([c['text'] for c in sorted(row_chars, key=lambda x: x['x0'])])
                if row_text.strip():
                    print(f"   Row Y={y}: {row_text[:80]}...")
        
        # 6. Check spacing and alignment
        if chars:
            x_positions = [c['x0'] for c in chars]
            unique_x = sorted(set([round(x/10)*10 for x in x_positions]))  # Round to nearest 10
            print(f"   Common X positions (columns): {unique_x[:10]}...")
        
        # 7. Export raw data for inspection
        debug_data = {
            'page_num': 13,
            'tables': tables,
            'text_lines': lines[:20],  # First 20 lines
            'char_count': len(chars),
            'y_positions': len(y_positions)
        }
        
        with open('pdf_debug_data.json', 'w') as f:
            json.dump(debug_data, f, indent=2, default=str)
        
        print(f"\n💾 Debug data saved to: pdf_debug_data.json")
        
        # 8. The brutal truth
        print(f"\n💣 THE BRUTAL TRUTH:")
        print(f"   This PDF likely has one of these issues:")
        print(f"   1. Tables are rendered as images, not text")
        print(f"   2. Text is positioned absolutely without table structure")
        print(f"   3. Tables use non-standard PDF table objects")
        print(f"   4. Text is fragmented into tiny pieces")
        print(f"   5. PDF was created by a tool that doesn't embed proper structure")
        
        # 9. Show what we actually need to work with
        print(f"\n🎯 WHAT WE'RE ACTUALLY DEALING WITH:")
        
        # Try to find a clear data row
        for line in lines[:50]:
            if line.strip() and len(line.split()) > 5:
                parts = line.split()
                if parts[0].isdigit():
                    print(f"   Example data row: {line}")
                    print(f"   Parts: {parts}")
                    break

if __name__ == "__main__":
    analyze_pdf_structure('S04479_RAPPORT_Rudi Matterne_0411_MO07202-7203_TV-wand (7-7).PDF')