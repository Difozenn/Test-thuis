#!/usr/bin/env python3
"""
Test script to debug ACCURA and BOERE PDF processing
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pdfplumber

def test_accura_processing(pdf_path):
    """Test ACCURA processing with debug output."""
    print(f"\n=== Testing ACCURA processing on {pdf_path} ===")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            aantal_items = 0
            aantal_sides = 0
            
            for page_num, page in enumerate(pdf.pages, 1):
                print(f"\nACCURA Page {page_num}:")
                try:
                    # Extract tables from the page
                    tables = page.extract_tables()
                    print(f"Found {len(tables)} tables on page {page_num}")
                    
                    for table_idx, table in enumerate(tables):
                        if not table or len(table) < 2:  # Need header + data
                            print(f"Table {table_idx}: Skipped (no header or data)")
                            continue
                        
                        print(f"Table {table_idx}: {len(table)} rows")
                        
                        # Look for table with L1, L2, B1, B2 columns
                        header = table[0] if table[0] else []
                        print(f"Header: {header}")
                        
                        l1_col = l2_col = b1_col = b2_col = -1
                        
                        for i, cell in enumerate(header):
                            if not cell:
                                continue
                            cell_upper = str(cell).upper()
                            if cell_upper == 'L1':
                                l1_col = i
                            elif cell_upper == 'L2':
                                l2_col = i
                            elif cell_upper == 'B1':
                                b1_col = i
                            elif cell_upper == 'B2':
                                b2_col = i
                        
                        print(f"Column positions: L1={l1_col}, L2={l2_col}, B1={b1_col}, B2={b2_col}")
                        
                        # Only process if we found L1/L2/B1/B2 columns
                        if all(col >= 0 for col in [l1_col, l2_col, b1_col, b2_col]):
                            print(f"✓ Found ACCURA table with L1/L2/B1/B2 columns")
                            
                            # Process data rows
                            for row_idx, row in enumerate(table[1:], 1):
                                if not row or len(row) <= max(l1_col, l2_col, b1_col, b2_col):
                                    continue
                                
                                # Check if row starts with a number (valid data row)
                                if not (row[0] and str(row[0]).strip().isdigit()):
                                    continue
                                
                                print(f"  Row {row_idx}: {row[:6] if len(row) > 6 else row}")  # Show first 6 cells
                                
                                # Count filled L1/L2/B1/B2 cells with actual work content
                                sides_in_row = 0
                                has_work = False
                                
                                for col in [l1_col, l2_col, b1_col, b2_col]:
                                    cell_content = str(row[col]).strip() if row[col] else ''
                                    col_name = ['L1', 'L2', 'B1', 'B2'][[l1_col, l2_col, b1_col, b2_col].index(col)]
                                    
                                    print(f"    {col_name} content: '{cell_content}'")
                                    
                                    # Check if cell has meaningful content (not empty, not "Te bestellen")
                                    if (cell_content and 
                                        cell_content.upper() not in ['', 'TE BESTELLEN', 'DUMMY', 'N/A'] and
                                        not cell_content.isdigit()):
                                        sides_in_row += 1
                                        has_work = True
                                        print(f"    ✓ {col_name} has valid content: '{cell_content}'")
                                
                                if has_work:
                                    aantal_items += 1
                                    aantal_sides += sides_in_row
                                    print(f"    ✓ Row {aantal_items}: {sides_in_row} sides with content")
                        else:
                            print(f"✗ Table {table_idx}: Not an ACCURA table (missing L1/L2/B1/B2 columns)")
                    
                except Exception as e_page:
                    print(f"Error processing page {page_num}: {e_page}")
                    continue
                    
    except Exception as e:
        print(f"ACCURA PDF parsing error: {e}")
        
    print(f"\nACCURA Final Result: {aantal_items} items, {aantal_sides} sides")
    return {'aantal_items': aantal_items, 'aantal_sides': aantal_sides}

def test_boere_processing(pdf_path):
    """Test BOERE processing with debug output."""
    print(f"\n=== Testing BOERE processing on {pdf_path} ===")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            item_count = 0
            
            for page_num, page in enumerate(pdf.pages, 1):
                print(f"\nBOERE Page {page_num}:")
                try:
                    # Extract tables from the page
                    tables = page.extract_tables()
                    print(f"Found {len(tables)} tables on page {page_num}")
                    
                    # Also get page text to check for Controle context
                    page_text = page.extract_text() or ""
                    has_controle_context = 'controle' in page_text.lower()
                    print(f"Controle context = {has_controle_context}")
                    
                    for table_idx, table in enumerate(tables):
                        if not table or len(table) < 2:  # Need header + data
                            print(f"Table {table_idx}: Skipped (no header or data)")
                            continue
                        
                        print(f"Table {table_idx}: {len(table)} rows")
                        
                        # Look for table with "Pro.methode" column in Controle context
                        header = table[0] if table[0] else []
                        print(f"Header: {header}")
                        
                        pro_methode_col = -1
                        
                        for i, cell in enumerate(header):
                            if not cell:
                                continue
                            cell_upper = str(cell).upper()
                            if 'PRO.METHODE' in cell_upper or 'METHODE' in cell_upper:
                                pro_methode_col = i
                                break
                        
                        print(f"Pro.methode column: {pro_methode_col}")
                        
                        if pro_methode_col >= 0 and has_controle_context:
                            print(f"✓ Found BOERE table (Controle context: {has_controle_context}, Pro.methode col: {pro_methode_col})")
                            
                            # Count data rows (skip header)
                            for row_idx, row in enumerate(table[1:], 1):
                                if row and len(row) > pro_methode_col:
                                    # Check if this row has meaningful data
                                    if any(str(cell).strip() for cell in row if cell):
                                        item_count += 1
                                        print(f"  Row {row_idx}: Found item (Total: {item_count})")
                            
                            print(f"BOERE table found {item_count} items on page {page_num}")
                        else:
                            print(f"✗ Table {table_idx}: Not a BOERE table (Pro.methode={pro_methode_col}, Controle={has_controle_context})")
                    
                except Exception as e:
                    print(f"Error processing page {page_num} for BOERE: {e}")
                    continue
            
            print(f"\nBOERE Final Result: {item_count} items")
            return item_count
            
    except Exception as e:
        print(f"Error parsing PDF for BOERE counts: {e}")
        import traceback
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    pdf_path = "/home/difusion/Projects/BarcodeMaster/S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF"
    
    print("PDF Debug Test Script")
    print("===================")
    
    if not os.path.exists(pdf_path):
        print(f"ERROR: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    # Test ACCURA processing
    accura_result = test_accura_processing(pdf_path)
    
    # Test BOERE processing
    boere_result = test_boere_processing(pdf_path)
    
    print("\n" + "="*50)
    print("SUMMARY:")
    print(f"ACCURA: {accura_result['aantal_items']} items, {accura_result['aantal_sides']} sides")
    print(f"BOERE: {boere_result} items")
    
    if accura_result['aantal_items'] == 0 and boere_result == 0:
        print("\n⚠️  Both processors found 0 items - this explains why database shows 0!")
    else:
        print(f"\n✓ At least one processor found items")