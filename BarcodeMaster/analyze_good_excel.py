#!/usr/bin/env python3
"""
ANALYZE GOOD EXCEL - Extract counts from the working ILovePDF Excel file
"""

import pandas as pd
import re
import os

def analyze_excel_structure(excel_file: str):
    """Analyze the structure of the Excel file"""
    
    print(f"📊 ANALYZING EXCEL STRUCTURE: {excel_file}")
    print("=" * 70)
    
    try:
        # Read all sheets
        excel_data = pd.read_excel(excel_file, sheet_name=None)
        
        print(f"📄 Found {len(excel_data)} sheets:")
        
        for sheet_name, df in excel_data.items():
            print(f"\n📋 Sheet: '{sheet_name}'")
            print(f"   Size: {len(df)} rows × {len(df.columns)} columns")
            print(f"   Columns: {list(df.columns)[:5]}{'...' if len(df.columns) > 5 else ''}")
            
            # Show first few rows
            print("   First 5 rows:")
            for i, row in df.head().iterrows():
                row_preview = ' | '.join([str(cell)[:20] for cell in row.values[:3]])
                print(f"     {i}: {row_preview}...")
            
            # Look for key patterns
            df_str = df.to_string().lower()
            
            patterns = {
                'nesting': 'nesting' in df_str,
                'opdeelzaag': 'opdeelzaag' in df_str,
                'controle': 'controle' in df_str,
                'massief': 'massief' in df_str,
                'magazijn': 'magazijn' in df_str,
                'aantal onderdelen': 'aantal onderdelen' in df_str,
                'beschrijving': 'beschrijving' in df_str,
                'fineer': 'fineer' in df_str,
                'finger': 'finger' in df_str,
                'l1 l2 b1 b2': all(col in df_str for col in ['l1', 'l2', 'b1', 'b2'])
            }
            
            found_patterns = [pattern for pattern, found in patterns.items() if found]
            if found_patterns:
                print(f"   📍 Key patterns found: {', '.join(found_patterns)}")
        
        return excel_data
    
    except Exception as e:
        print(f"❌ Failed to analyze Excel: {e}")
        return None

def extract_counts_from_good_excel(excel_file: str) -> dict:
    """Extract exact counts from the good Excel file"""
    
    print(f"\n🎯 EXTRACTING COUNTS FROM: {excel_file}")
    print("=" * 50)
    
    try:
        # Read the Excel file
        excel_data = pd.read_excel(excel_file, sheet_name=None)
        
        total_nesting = 0
        total_boere = 0
        total_accura = 0
        
        for sheet_name, df in excel_data.items():
            print(f"\n📋 Analyzing sheet: '{sheet_name}'")
            
            # Convert to string for pattern matching
            sheet_text = df.to_string().lower()
            
            # Count NESTING - look for "aantal onderdelen" patterns
            aantal_matches = re.findall(r'aantal onderdelen[:\s]*(\d+)', sheet_text)
            if aantal_matches:
                sheet_aantal = [int(x) for x in aantal_matches if 5 <= int(x) <= 100]
                if len(sheet_aantal) >= 2:
                    nesting_count = sheet_aantal[0] + sheet_aantal[1]
                    total_nesting += nesting_count
                    print(f"   NESTING: {sheet_aantal[0]} + {sheet_aantal[1]} = {nesting_count}")
                elif len(sheet_aantal) == 1:
                    total_nesting += sheet_aantal[0]
                    print(f"   NESTING: {sheet_aantal[0]}")
            
            # Count BOERE - numbered items in "beschrijving" tables
            if ('beschrijving' in sheet_text and 'aantal stuks' in sheet_text):
                boere_count = 0
                
                # Look for numbered rows
                for idx, row in df.iterrows():
                    first_cell = str(row.iloc[0]).strip()
                    if re.match(r'^\d+$', first_cell):
                        row_text = ' '.join([str(cell) for cell in row.values]).lower()
                        if 'te bestellen' not in row_text:
                            boere_count += 1
                
                if boere_count > 0:
                    total_boere += boere_count
                    print(f"   BOERE: {boere_count} items from quality control table")
            
            # Count ACCURA - items with edge processing (L1, L2, B1, B2 or Fineer)
            if any(col in sheet_text for col in ['l1', 'l2', 'b1', 'b2', 'fineer', 'finger']):
                accura_count = 0
                
                # Look for numbered rows with edge processing
                for idx, row in df.iterrows():
                    first_cell = str(row.iloc[0]).strip()
                    if re.match(r'^\d+$', first_cell):
                        row_text = ' '.join([str(cell) for cell in row.values]).lower()
                        
                        # Check for edge processing indicators
                        if any(indicator in row_text for indicator in [
                            'fineer', 'finger', 'standaard', 'l1', 'l2', 'b1', 'b2'
                        ]) or re.search(r'\d+mm', row_text):
                            accura_count += 1
                
                if accura_count > 0:
                    total_accura += accura_count
                    print(f"   ACCURA: {accura_count} items with edge processing")
        
        print(f"\n📊 TOTAL COUNTS:")
        print(f"NESTING: {total_nesting}")
        print(f"BOERE: {total_boere}")
        print(f"ACCURA: {total_accura}")
        
        return {
            'nesting': total_nesting,
            'boere': total_boere,
            'accura': total_accura,
            'method': 'Good Excel Analysis'
        }
    
    except Exception as e:
        print(f"❌ Count extraction failed: {e}")
        return None

def test_good_excel():
    """Test the good Excel file analysis"""
    
    excel_file = '1.xlsx'
    
    if not os.path.exists(excel_file):
        print(f"❌ Excel file not found: {excel_file}")
        return
    
    print("Expected: NESTING=52, BOERE=62, ACCURA=44")
    print("-" * 70)
    
    # Analyze structure first
    excel_data = analyze_excel_structure(excel_file)
    
    if excel_data:
        # Extract counts
        counts = extract_counts_from_good_excel(excel_file)
        
        if counts:
            print(f"\n✅ FINAL COMPARISON:")
            print(f"NESTING: {counts['nesting']} (expected 52) {'✅' if counts['nesting'] == 52 else '❌'}")
            print(f"BOERE: {counts['boere']} (expected 62) {'✅' if counts['boere'] == 62 else '❌'}")
            print(f"ACCURA: {counts['accura']} (expected 44) {'✅' if counts['accura'] == 44 else '❌'}")
            
            # Calculate accuracy
            total_expected = 52 + 62 + 44
            total_actual = counts['nesting'] + counts['boere'] + counts['accura']
            accuracy = (min(total_actual, total_expected) / total_expected) * 100
            
            print(f"\n📈 ACCURACY: {accuracy:.1f}%")
            
            if counts['nesting'] == 52 and counts['boere'] == 62 and counts['accura'] == 44:
                print("🎉 PERFECT EXTRACTION!")

if __name__ == "__main__":
    test_good_excel()