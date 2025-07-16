#!/usr/bin/env python3
"""
Debug BOERE extraction - Find exactly where the 139 items are located
"""

import pdfplumber
import re

def debug_boere_extraction(pdf_path: str):
    """Debug the BOERE extraction by examining each page carefully"""
    
    total_digit_items = 0
    total_te_bestellen = 0
    
    with pdfplumber.open(pdf_path) as pdf:
        print("=== DEBUGGING BOERE EXTRACTION ===")
        print("Looking for all items with N° (digits) from page 11-25")
        print("Excluding items with 'TE BESTELLEN' in Pro.methode")
        print()
        
        # Process pages 11-25 (Controle to before Magazijn)
        for page_num in range(11, 26):
            if page_num > len(pdf.pages):
                continue
                
            page = pdf.pages[page_num-1]
            text = page.extract_text() or ""
            lines = text.split('\n')
            
            page_digit_count = 0
            page_te_bestellen = 0
            
            print(f"\n--- PAGE {page_num} ---")
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Look for lines that start with digits (N° column)
                if re.match(r'^\d+\s', line):
                    # Extract the number at the start
                    match = re.match(r'^(\d+)', line)
                    if match:
                        item_number = match.group(1)
                        
                        # Check if this line contains "Te bestellen"
                        if 'Te bestellen' in line or 'TE BESTELLEN' in line.upper():
                            page_te_bestellen += 1
                            total_te_bestellen += 1
                            print(f"  Line {line_num:2d}: N° {item_number} - TE BESTELLEN - {line[:80]}...")
                        else:
                            page_digit_count += 1
                            total_digit_items += 1
                            print(f"  Line {line_num:2d}: N° {item_number} - VALID - {line[:80]}...")
            
            print(f"Page {page_num} total: {page_digit_count} valid items, {page_te_bestellen} Te bestellen")
            
        print(f"\n=== FINAL TOTALS ===")
        print(f"Valid BOERE items (with N°, not Te bestellen): {total_digit_items}")
        print(f"Te bestellen items excluded: {total_te_bestellen}")
        print(f"Total items with N°: {total_digit_items + total_te_bestellen}")
        print(f"Expected BOERE: 139")
        print(f"Difference: {139 - total_digit_items}")

if __name__ == "__main__":
    debug_boere_extraction('S04479_RAPPORT_Rudi Matterne_0411_MO07202-7203_TV-wand (7-7).PDF')