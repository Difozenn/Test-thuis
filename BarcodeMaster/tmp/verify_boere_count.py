#!/usr/bin/env python3
"""
Verify BOERE count - Double check the expected 139 count
"""

import pdfplumber
import re

def verify_boere_count(pdf_path: str):
    """Verify the actual BOERE count by examining the PDF structure"""
    
    with pdfplumber.open(pdf_path) as pdf:
        print("=== VERIFYING BOERE COUNT ===")
        print("Looking for section headers and item counts...")
        print()
        
        # First, let's see what the PDF itself says about item counts
        for page_num in range(1, min(30, len(pdf.pages) + 1)):
            page = pdf.pages[page_num-1]
            text = page.extract_text() or ""
            
            # Look for "Aantal onderdelen" statements
            if "Aantal onderdelen" in text:
                lines = text.split('\n')
                for line in lines:
                    if "Aantal onderdelen" in line:
                        print(f"Page {page_num}: {line.strip()}")
            
            # Look for section headers
            if any(header in text.upper() for header in ['CONTROLE', 'MASSIEF', 'MAGAZIJN']):
                lines = text.split('\n')[:10]
                header_text = ' '.join(lines).upper()
                if 'CONTROLE' in header_text:
                    print(f"Page {page_num}: CONTROLE section starts")
                elif 'MASSIEF' in header_text and 'CONTROLE' not in header_text:
                    print(f"Page {page_num}: MASSIEF section starts")
                elif 'MAGAZIJN' in header_text:
                    print(f"Page {page_num}: MAGAZIJN section starts")
        
        print("\n=== MANUAL COUNT VERIFICATION ===")
        
        # Count all items with N° from Controle (page 11) to before Magazijn (page 26)
        total_items = 0
        total_te_bestellen = 0
        
        print("Counting all items with N° from pages 11-25:")
        
        for page_num in range(11, 26):
            if page_num > len(pdf.pages):
                continue
                
            page = pdf.pages[page_num-1]
            text = page.extract_text() or ""
            lines = text.split('\n')
            
            page_items = 0
            page_te_bestellen = 0
            
            for line in lines:
                line = line.strip()
                
                # Look for lines that start with digits (N° column)
                if re.match(r'^\d+\s', line):
                    if 'Te bestellen' in line or 'TE BESTELLEN' in line.upper():
                        page_te_bestellen += 1
                        total_te_bestellen += 1
                    else:
                        page_items += 1
                        total_items += 1
            
            if page_items > 0 or page_te_bestellen > 0:
                print(f"  Page {page_num}: {page_items} items, {page_te_bestellen} Te bestellen")
        
        print(f"\nTotal items with N° (excluding Te bestellen): {total_items}")
        print(f"Total Te bestellen items: {total_te_bestellen}")
        print(f"Grand total items with N°: {total_items + total_te_bestellen}")
        
        # Let's also check what user originally said about the count
        print(f"\nUser originally said BOERE should be: 139")
        print(f"Our count shows: {total_items}")
        print(f"Difference: {total_items - 139}")
        
        if total_items != 139:
            print(f"\n🔍 The expected 139 might be incorrect!")
            print(f"📊 Actual count from PDF appears to be: {total_items}")

if __name__ == "__main__":
    verify_boere_count('S04479_RAPPORT_Rudi Matterne_0411_MO07202-7203_TV-wand (7-7).PDF')