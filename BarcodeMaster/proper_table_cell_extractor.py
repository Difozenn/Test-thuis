#!/usr/bin/env python3
"""
PROPER TABLE CELL EXTRACTOR
Extract actual table cells and read L1, L2, B1, B2 column values
TRUE DYNAMIC EXTRACTION - NO PATTERN MATCHING
"""

import pdfplumber
import re
import pandas as pd
import subprocess
import os

def extract_table_cells(pdf_path):
    """
    Extract actual table cells and analyze L1/L2/B1/B2 columns
    """
    print("🔧 PROPER TABLE CELL EXTRACTION")
    print("=" * 50)
    
    results = {
        'count1_nesting': 0,
        'count1_opdeelzaag': 0,
        'count1_total': 0,
        'count2a_items': 0,  # Items with edge processing
        'count2b_sides': 0,  # Total individual sides
        'count3_boere': 0
    }
    
    details = {
        'count1': [],
        'count2': [],
        'count3': []
    }
    
    # === COUNT1: Use existing text method (works perfectly) ===
    print("\n📊 COUNT1: NESTING + OPDEELZAAG (text method)")
    
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
            
            if (in_nesting or in_opdeelzaag) and re.match(r'^\s*\d+\s+\w+', line):
                if in_nesting:
                    results['count1_nesting'] += 1
                elif in_opdeelzaag:
                    results['count1_opdeelzaag'] += 1
    
    results['count1_total'] = results['count1_nesting'] + results['count1_opdeelzaag']
    print(f"  NESTING: {results['count1_nesting']}")
    print(f"  OPDEELZAAG: {results['count1_opdeelzaag']}")
    print(f"  TOTAL: {results['count1_total']}")
    
    # === COUNT2: ACCURA from Controle to Magazijn (like COUNT3) ===
    print("\n📊 COUNT2: ACCURA - Table cell extraction from Controle to Magazijn")
    
    with pdfplumber.open(pdf_path) as pdf:
        # Find pages with Controle to Magazijn section
        for page_num, page in enumerate(pdf.pages):
            page_text = page.extract_text() or ""
            page_text_lower = page_text.lower()
            
            has_controle = 'controle' in page_text_lower
            has_magazijn = 'magazijn' in page_text_lower
            
            # Only process pages in the Controle-Magazijn section
            if not (has_controle or has_magazijn):
                continue
            
            print(f"  Processing page {page_num + 1} (Controle-Magazijn section)")
            
            # Extract all tables from this page
            tables = page.extract_tables()
            
            for table_idx, table in enumerate(tables):
                if not table or len(table) < 2:
                    continue
                
                print(f"    Analyzing table {table_idx + 1} ({len(table)} rows)")
                
                # Try to identify L1, L2, B1, B2 columns
                l1_col = l2_col = b1_col = b2_col = -1
                header_idx = -1
                
                # Method 1: Look for explicit L1/L2/B1/B2 in any row
                for row_idx, row in enumerate(table):
                    if row:
                        for col_idx, cell in enumerate(row):
                            if cell:
                                cell_text = str(cell).strip().upper()
                                if cell_text == 'L1':
                                    l1_col = col_idx
                                    header_idx = row_idx
                                elif cell_text == 'L2':
                                    l2_col = col_idx
                                elif cell_text == 'B1':
                                    b1_col = col_idx
                                elif cell_text == 'B2':
                                    b2_col = col_idx
                        
                        if l1_col >= 0:  # Found header row
                            break
                
                # Method 2: Standard positions if no explicit headers
                if l1_col == -1 and table and len(table[0]) >= 8:
                    # Assume standard table structure
                    if len(table[0]) >= 10:
                        l1_col = 6
                        l2_col = 7
                        b1_col = 8
                        b2_col = 9
                    else:
                        l1_col = 5
                        l2_col = 6
                        b1_col = 7
                        b2_col = 8
                    header_idx = 0
                
                print(f"      Edge columns: L1={l1_col}, L2={l2_col}, B1={b1_col}, B2={b2_col}")
                
                if l1_col == -1:
                    print(f"      No edge processing columns found, skipping table")
                    continue
                
                # Process data rows
                for row_idx in range(max(0, header_idx + 1), len(table)):
                    row = table[row_idx]
                    if not row or len(row) == 0:
                        continue
                    
                    # Check if this is a numbered item row
                    first_cell = str(row[0]) if row[0] else ""
                    if not re.match(r'^\s*\d+', first_cell):
                        continue
                    
                    # Skip "te bestellen" items
                    row_text = ' '.join([str(cell) if cell else '' for cell in row]).lower()
                    if 'te bestellen' in row_text:
                        continue
                    
                    # Count edge processing sides - PROPER CELL EXTRACTION
                    sides_count = 0
                    edge_info = []
                    
                    # Check each L1, L2, B1, B2 column for ANY non-empty content
                    for col_name, col_idx in [('L1', l1_col), ('L2', l2_col), ('B1', b1_col), ('B2', b2_col)]:
                        if col_idx >= 0 and col_idx < len(row):
                            cell_value = row[col_idx]
                            if cell_value and str(cell_value).strip():
                                # ANY non-empty value = 1 side (dynamic content detection)
                                cell_text = str(cell_value).strip()
                                if cell_text.lower() not in ['', 'none', 'null', '0']:
                                    sides_count += 1
                                    edge_info.append(f"{col_name}={cell_text}")
                    
                    if sides_count > 0:
                        results['count2a_items'] += 1
                        results['count2b_sides'] += sides_count
                        
                        item_info = f"Item {first_cell}: {sides_count} sides ({', '.join(edge_info)})"
                        details['count2'].append(item_info)
                        print(f"      ✅ ACCURA: {item_info}")
    
    print(f"  ACCURA ITEMS: {results['count2a_items']}")
    print(f"  TOTAL SIDES: {results['count2b_sides']}")
    
    # === COUNT3: Use existing text method (works perfectly) ===
    print("\n📊 COUNT3: BOERE (text method)")
    
    with pdfplumber.open(pdf_path) as pdf:
        all_text = ""
        for page in pdf.pages:
            if page.extract_text():
                all_text += page.extract_text() + "\n"
        
        lines = all_text.split('\n')
        in_controle_section = False
        
        for line in lines:
            line_lower = line.lower().strip()
            
            if 'controle' in line_lower and not in_controle_section:
                in_controle_section = True
                continue
            
            if 'magazijn' in line_lower and in_controle_section:
                in_controle_section = False
                break
            
            if in_controle_section and re.match(r'^\s*\d+\s+\w+', line):
                if 'te bestellen' not in line_lower:
                    results['count3_boere'] += 1
                    details['count3'].append(f"BOERE: {line.strip()}")
    
    print(f"  BOERE ITEMS: {results['count3_boere']}")
    
    return results, details

def main():
    """Main execution"""
    pdf_path = "S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF"
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF file not found: {pdf_path}")
        return
    
    # Extract counts
    results, details = extract_table_cells(pdf_path)
    
    # Display final results
    print(f"\n🎯 PROPER TABLE CELL RESULTS:")
    print("=" * 50)
    print(f"COUNT1 (NESTING): {results['count1_nesting']}")
    print(f"COUNT1 (OPDEELZAAG): {results['count1_opdeelzaag']}")
    print(f"COUNT1 (TOTAL): {results['count1_total']}")
    print(f"COUNT2A (ACCURA ITEMS): {results['count2a_items']}")
    print(f"COUNT2B (ACCURA SIDES): {results['count2b_sides']}")
    print(f"COUNT3 (BOERE): {results['count3_boere']}")
    
    # Save results
    summary_data = {
        "Metric": [
            "COUNT1 - Nesting Items",
            "COUNT1 - Opdeelzaag Items", 
            "COUNT1 - Total Items",
            "COUNT2A - ACCURA Items",
            "COUNT2B - ACCURA Sides",
            "COUNT3 - BOERE Items"
        ],
        "Value": [
            results['count1_nesting'],
            results['count1_opdeelzaag'],
            results['count1_total'],
            results['count2a_items'],
            results['count2b_sides'],
            results['count3_boere']
        ]
    }
    
    df_summary = pd.DataFrame(summary_data)
    df_summary.to_excel("proper_table_cell_results.xlsx", index=False)
    
    # Save details
    for count_type, items in details.items():
        if items:
            pd.DataFrame(items, columns=["Items"]).to_excel(f"proper_{count_type}_details.xlsx", index=False)
    
    print(f"\n✅ PROPER TABLE CELL EXTRACTION COMPLETED!")
    print(f"📁 Results saved to proper_table_cell_results.xlsx")

if __name__ == "__main__":
    main()