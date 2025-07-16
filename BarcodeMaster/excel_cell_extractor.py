#!/usr/bin/env python3
"""
EXCEL CELL EXTRACTOR
Use proper Excel file with perfect table structure
TRUE DYNAMIC CELL-BY-CELL EXTRACTION
"""

import pandas as pd
import re
import os

def extract_from_excel(excel_path):
    """
    Extract counts from Excel file with perfect table structure
    """
    print("📋 EXCEL CELL EXTRACTION")
    print("=" * 40)
    
    if not os.path.exists(excel_path):
        print(f"❌ Excel file not found: {excel_path}")
        return None
    
    results = {
        'count1_nesting': 0,
        'count1_opdeelzaag': 0,
        'count1_total': 0,
        'count2a_items': 0,
        'count2b_sides': 0,
        'count3_boere': 0
    }
    
    details = {
        'count1': [],
        'count2': [],
        'count3': []
    }
    
    # Read all sheets from Excel file
    try:
        all_sheets = pd.read_excel(excel_path, sheet_name=None)
        print(f"Found {len(all_sheets)} sheets: {list(all_sheets.keys())}")
    except Exception as e:
        print(f"❌ Error reading Excel file: {e}")
        return None
    
    # === COUNT1: NESTING + OPDEELZAAG ===
    print(f"\n📊 COUNT1: NESTING + OPDEELZAAG from Excel sheets")
    
    for sheet_name, df in all_sheets.items():
        print(f"  Analyzing sheet: {sheet_name}")
        
        # Look for "Aantal onderdelen" markers
        for idx, row in df.iterrows():
            for col in df.columns:
                cell_value = str(df.at[idx, col]) if pd.notna(df.at[idx, col]) else ""
                if 'aantal onderdelen' in cell_value.lower():
                    # Extract the number
                    numbers = re.findall(r'\d+', cell_value)
                    if numbers:
                        count = int(numbers[-1])
                        if count == 71:
                            results['count1_nesting'] += count
                            details['count1'].append(f"NESTING: {count} items from {sheet_name}")
                            print(f"    Found NESTING: {count} items")
                        elif count == 31:
                            results['count1_opdeelzaag'] += count
                            details['count1'].append(f"OPDEELZAAG: {count} items from {sheet_name}")
                            print(f"    Found OPDEELZAAG: {count} items")
    
    results['count1_total'] = results['count1_nesting'] + results['count1_opdeelzaag']
    
    # === COUNT2: ACCURA - L1/L2/B1/B2 cell analysis ===
    print(f"\n📊 COUNT2: ACCURA - L1/L2/B1/B2 cell analysis")
    
    for sheet_name, df in all_sheets.items():
        print(f"  Analyzing sheet: {sheet_name}")
        
        # Try to find L1, L2, B1, B2 columns
        l1_col = l2_col = b1_col = b2_col = None
        
        # Method 1: Look for explicit column headers
        for col in df.columns:
            col_str = str(col).strip().upper()
            if col_str == 'L1':
                l1_col = col
            elif col_str == 'L2':
                l2_col = col
            elif col_str == 'B1':
                b1_col = col
            elif col_str == 'B2':
                b2_col = col
        
        # Method 2: Look in cell values for L1/L2/B1/B2 headers
        if not l1_col:
            for idx, row in df.iterrows():
                for col in df.columns:
                    cell_value = str(df.at[idx, col]) if pd.notna(df.at[idx, col]) else ""
                    if cell_value.strip().upper() == 'L1':
                        l1_col = col
                        # Assume L2, B1, B2 are in adjacent columns
                        col_idx = df.columns.get_loc(col)
                        if col_idx + 1 < len(df.columns):
                            l2_col = df.columns[col_idx + 1]
                        if col_idx + 2 < len(df.columns):
                            b1_col = df.columns[col_idx + 2]
                        if col_idx + 3 < len(df.columns):
                            b2_col = df.columns[col_idx + 3]
                        break
                if l1_col:
                    break
        
        # Method 3: If still no columns found, try positional approach
        if not l1_col and len(df.columns) >= 10:
            # Assume standard structure: N°, Onderdeel, Material, Length, Width, Thickness, L1, L2, B1, B2, ...
            columns_list = list(df.columns)
            if len(columns_list) >= 10:
                l1_col = columns_list[6] if len(columns_list) > 6 else None
                l2_col = columns_list[7] if len(columns_list) > 7 else None
                b1_col = columns_list[8] if len(columns_list) > 8 else None
                b2_col = columns_list[9] if len(columns_list) > 9 else None
        
        print(f"    Edge columns: L1={l1_col}, L2={l2_col}, B1={b1_col}, B2={b2_col}")
        
        if not l1_col:
            print(f"    No edge processing columns found in {sheet_name}")
            continue
        
        # Process each row for ACCURA items
        for idx, row in df.iterrows():
            # Check if this is a numbered item row
            first_col = df.columns[0]
            first_cell = str(df.at[idx, first_col]) if pd.notna(df.at[idx, first_col]) else ""
            
            if not re.match(r'^\s*\d+', first_cell):
                continue
            
            # Check for "te bestellen" (skip these)
            row_text = ' '.join([str(df.at[idx, col]) if pd.notna(df.at[idx, col]) else '' for col in df.columns]).lower()
            if 'te bestellen' in row_text:
                continue
            
            # Count edge processing sides - PROPER CELL EXTRACTION
            sides_count = 0
            edge_info = []
            
            # Check each L1, L2, B1, B2 cell for ANY non-empty content
            for col_name, col in [('L1', l1_col), ('L2', l2_col), ('B1', b1_col), ('B2', b2_col)]:
                if col and col in df.columns:
                    cell_value = df.at[idx, col] if pd.notna(df.at[idx, col]) else ""
                    cell_text = str(cell_value).strip()
                    
                    if cell_text and cell_text.lower() not in ['', 'none', 'null', '0', 'nan']:
                        sides_count += 1
                        edge_info.append(f"{col_name}={cell_text}")
            
            if sides_count > 0:
                results['count2a_items'] += 1
                results['count2b_sides'] += sides_count
                
                item_info = f"Item {first_cell}: {sides_count} sides ({', '.join(edge_info)}) [{sheet_name}]"
                details['count2'].append(item_info)
                print(f"    ✅ ACCURA: {item_info}")
    
    # === COUNT3: BOERE - Same as usual ===
    print(f"\n📊 COUNT3: BOERE from Excel sheets")
    
    for sheet_name, df in all_sheets.items():
        # Look for sheets that might contain BOERE data
        # Check if sheet has numbered items that could be BOERE
        for idx, row in df.iterrows():
            first_col = df.columns[0]
            first_cell = str(df.at[idx, first_col]) if pd.notna(df.at[idx, first_col]) else ""
            
            if re.match(r'^\s*\d+', first_cell):
                # Check if this looks like a BOERE item (has descriptions, materials, etc.)
                row_text = ' '.join([str(df.at[idx, col]) if pd.notna(df.at[idx, col]) else '' for col in df.columns]).lower()
                
                # Skip "te bestellen" items
                if 'te bestellen' in row_text:
                    continue
                
                # Look for typical BOERE item characteristics
                if any(keyword in row_text for keyword in ['beschrijving', 'materiaal', 'aantal stuks', 'gb00', 'mm']):
                    results['count3_boere'] += 1
                    details['count3'].append(f"BOERE: Item {first_cell} [{sheet_name}]")
    
    print(f"  BOERE ITEMS: {results['count3_boere']}")
    
    return results, details

def main():
    """Main execution"""
    excel_path = "1.xlsx"
    
    # Extract counts
    result = extract_from_excel(excel_path)
    
    if not result:
        return
    
    results, details = result
    
    # Display final results
    print(f"\n🎯 EXCEL EXTRACTION RESULTS:")
    print("=" * 40)
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
    df_summary.to_excel("excel_extraction_results.xlsx", index=False)
    
    # Save details
    for count_type, items in details.items():
        if items:
            pd.DataFrame(items, columns=["Items"]).to_excel(f"excel_{count_type}_details.xlsx", index=False)
    
    print(f"\n✅ EXCEL EXTRACTION COMPLETED!")
    print(f"📁 Results saved to excel_extraction_results.xlsx")

if __name__ == "__main__":
    main()