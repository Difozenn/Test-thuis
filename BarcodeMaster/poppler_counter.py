#!/usr/bin/env python3
"""
POPPLER COUNTER - Extract exact counts from Poppler-utils CSV
"""

import pandas as pd
import re

def extract_counts_from_poppler_csv(csv_file: str) -> dict:
    """Extract exact NESTING, BOERE, ACCURA counts from Poppler CSV"""
    
    print("🎯 EXTRACTING COUNTS FROM POPPLER CSV")
    print("=" * 50)
    
    try:
        # Read the CSV
        df = pd.read_csv(csv_file)
        print(f"📄 Loaded {len(df)} lines from CSV")
        
        # Extract NESTING count from "Aantal onderdelen" markers
        aantal_lines = df[df['content'].str.contains('Aantal onderdelen:', na=False)]
        aantal_counts = []
        
        print("\n🔍 NESTING - 'Aantal onderdelen' markers:")
        for _, row in aantal_lines.iterrows():
            content = str(row['content'])
            numbers = re.findall(r'Aantal onderdelen:\s*(\d+)', content)
            if numbers:
                count = int(numbers[0])
                if 5 <= count <= 100:  # Reasonable range
                    aantal_counts.append(count)
                    print(f"   Line {row['line_num']}: {count}")
        
        # NESTING = first two counts (as per user specification)
        nesting_count = 0
        if len(aantal_counts) >= 2:
            nesting_count = aantal_counts[0] + aantal_counts[1]
            print(f"✅ NESTING: {aantal_counts[0]} + {aantal_counts[1]} = {nesting_count}")
        
        # Extract BOERE count from quality control tables
        print("\n🔍 BOERE - Quality control tables:")
        
        # Find lines with "Beschrijving" and "Aantal stuks" headers (BOERE tables)
        boere_header_lines = df[df['content'].str.contains('Beschrijving.*Aantal stuks', na=False)]
        
        boere_count = 0
        for _, header_row in boere_header_lines.iterrows():
            header_line_num = header_row['line_num']
            print(f"   Found BOERE table header at line {header_line_num}")
            
            # Count numbered rows after this header until next section
            table_rows = df[
                (df['line_num'] > header_line_num) & 
                (df['line_num'] < header_line_num + 50) &  # Look in next 50 lines
                (df['is_numbered'] == True)
            ]
            
            for _, row in table_rows.iterrows():
                content = str(row['content']).lower()
                # Exclude "te bestellen" items as per user rule
                if 'te bestellen' not in content:
                    boere_count += 1
                    print(f"   Line {row['line_num']}: BOERE item")
        
        print(f"✅ BOERE: {boere_count} items from quality control tables")
        
        # Extract ACCURA count from NESTING items with edge processing
        print("\n🔍 ACCURA - NESTING items with edge processing:")
        
        # Find numbered rows that have edge processing data (L1, L2, B1, B2, Fineer, etc.)
        numbered_rows = df[df['is_numbered'] == True]
        
        accura_count = 0
        for _, row in numbered_rows.iterrows():
            content = str(row['content']).lower()
            
            # Check for edge processing indicators
            if any(indicator in content for indicator in [
                'fineer', 'finger', 'standaard', 'l1', 'l2', 'b1', 'b2'
            ]) or re.search(r'\d+mm', content):
                
                # Make sure it's not in a BOERE/Massief section
                if not any(section in content for section in ['massief', 'beschrijving']):
                    accura_count += 1
                    if accura_count <= 5:  # Show first 5 examples
                        print(f"   Line {row['line_num']}: ACCURA item")
        
        print(f"✅ ACCURA: {accura_count} items with edge processing")
        
        results = {
            'nesting': nesting_count,
            'boere': boere_count,
            'accura': accura_count,
            'method': 'Poppler CSV Analysis'
        }
        
        return results
    
    except Exception as e:
        print(f"❌ Failed to extract counts: {e}")
        return None

def test_poppler_counter():
    """Test the Poppler counter"""
    
    csv_file = 'S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7)_poppler.csv'
    
    if not os.path.exists(csv_file):
        print(f"❌ CSV not found: {csv_file}")
        return
    
    print("Expected: NESTING=52, BOERE=62, ACCURA=44")
    print("-" * 70)
    
    # Extract counts
    counts = extract_counts_from_poppler_csv(csv_file)
    
    if counts:
        print(f"\n📊 FINAL RESULTS:")
        print(f"NESTING: {counts['nesting']} (expected 52) {'✅' if counts['nesting'] == 52 else '❌'}")
        print(f"BOERE: {counts['boere']} (expected 62) {'✅' if counts['boere'] == 62 else '❌'}")
        print(f"ACCURA: {counts['accura']} (expected 44) {'✅' if counts['accura'] == 44 else '❌'}")
        
        # Calculate accuracy
        total_expected = 52 + 62 + 44
        total_actual = counts['nesting'] + counts['boere'] + counts['accura']
        accuracy = (total_actual / total_expected) * 100 if total_expected > 0 else 0
        
        print(f"\n📈 ACCURACY: {accuracy:.1f}%")
        
        if counts['nesting'] == 52 and counts['boere'] == 62 and counts['accura'] == 44:
            print("🎉 PERFECT EXTRACTION!")

if __name__ == "__main__":
    import os
    test_poppler_counter()