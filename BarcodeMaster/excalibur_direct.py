#!/usr/bin/env python3
"""
EXCALIBUR DIRECT - Use excalibur-py library directly
"""

import os
import pandas as pd

def test_excalibur_direct():
    """Test excalibur-py library directly"""
    
    pdf_path = 'S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF'
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print("⚡ TESTING EXCALIBUR-PY DIRECT")
    print("=" * 70)
    
    try:
        import camelot
        
        print("🔍 Using Camelot (Excalibur backend)...")
        
        # Excalibur is built on Camelot, so we can use camelot directly
        print(f"📄 Processing: {os.path.basename(pdf_path)}")
        
        # Method 1: Lattice (for tables with borders)
        print("\n📊 Method 1: Lattice mode...")
        tables_lattice = camelot.read_pdf(pdf_path, flavor='lattice', pages='all')
        
        if tables_lattice:
            print(f"✅ Found {len(tables_lattice)} tables with lattice")
            
            # Save to CSV
            csv_file_lattice = pdf_path.replace('.PDF', '_excalibur_lattice.csv').replace('.pdf', '_excalibur_lattice.csv')
            
            all_tables = []
            for i, table in enumerate(tables_lattice):
                df = table.df
                df['_table_num'] = i + 1
                df['_page'] = table.page
                df['_accuracy'] = table.accuracy
                all_tables.append(df)
            
            if all_tables:
                combined_df = pd.concat(all_tables, ignore_index=True)
                combined_df.to_csv(csv_file_lattice, index=False)
                
                print(f"✅ Lattice CSV saved: {csv_file_lattice}")
                print(f"   Total rows: {len(combined_df)}")
                
                # Show sample
                print("   Sample data:")
                for i, row in combined_df.head(3).iterrows():
                    print(f"     Row {i}: {str(row.iloc[0])[:30]}...")
        
        # Method 2: Stream (for tables without borders)
        print("\n📊 Method 2: Stream mode...")
        tables_stream = camelot.read_pdf(pdf_path, flavor='stream', pages='all')
        
        if tables_stream:
            print(f"✅ Found {len(tables_stream)} tables with stream")
            
            # Save to CSV
            csv_file_stream = pdf_path.replace('.PDF', '_excalibur_stream.csv').replace('.pdf', '_excalibur_stream.csv')
            
            all_tables = []
            for i, table in enumerate(tables_stream):
                df = table.df
                df['_table_num'] = i + 1
                df['_page'] = table.page
                all_tables.append(df)
            
            if all_tables:
                combined_df = pd.concat(all_tables, ignore_index=True)
                combined_df.to_csv(csv_file_stream, index=False)
                
                print(f"✅ Stream CSV saved: {csv_file_stream}")
                print(f"   Total rows: {len(combined_df)}")
        
        # Analyze results
        results = []
        
        if 'csv_file_lattice' in locals():
            lattice_analysis = analyze_excalibur_csv(csv_file_lattice)
            results.append(('Lattice', csv_file_lattice, lattice_analysis))
        
        if 'csv_file_stream' in locals():
            stream_analysis = analyze_excalibur_csv(csv_file_stream)
            results.append(('Stream', csv_file_stream, stream_analysis))
        
        # Show results
        print(f"\n🏆 EXCALIBUR RESULTS:")
        if results:
            for method, file, analysis in results:
                quality = analysis.get('quality', 0) if analysis else 0
                print(f"  {method}: {file} (quality: {quality}/10)")
            
            # Recommend best
            best = max(results, key=lambda x: x[2].get('quality', 0) if x[2] else 0)
            print(f"\n🎯 RECOMMENDED: {best[0]} - {best[1]}")
            return best[1]
        else:
            print("❌ No results")
            return None
    
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure camelot-py is installed: pip install camelot-py[cv]")
        return None
    except Exception as e:
        print(f"❌ Excalibur error: {e}")
        return None

def analyze_excalibur_csv(csv_file: str):
    """Analyze Excalibur CSV quality"""
    
    print(f"\n📈 ANALYZING: {os.path.basename(csv_file)}")
    
    try:
        df = pd.read_csv(csv_file)
        
        # Convert to string for pattern matching
        content = df.to_string().lower()
        
        patterns = {
            'total_rows': len(df),
            'total_cols': len(df.columns),
            'nesting': content.count('nesting'),
            'aantal_onderdelen': content.count('aantal onderdelen'),
            'controle': content.count('controle'),
            'magazijn': content.count('magazijn'),
            'beschrijving': content.count('beschrijving'),
            'fineer': content.count('fineer'),
            'numbered_rows': len([i for i, row in df.iterrows() if str(row.iloc[0]).strip().isdigit()]),
        }
        
        print(f"   Rows: {patterns['total_rows']}, Cols: {patterns['total_cols']}")
        print(f"   Numbered rows: {patterns['numbered_rows']}")
        
        found_patterns = []
        for pattern, count in patterns.items():
            if pattern not in ['total_rows', 'total_cols', 'numbered_rows'] and count > 0:
                found_patterns.append(f"{pattern}={count}")
        
        if found_patterns:
            print(f"   Key patterns: {', '.join(found_patterns)}")
        
        # Quality scoring
        quality = 0
        if patterns['total_rows'] > 50: quality += 2
        if patterns['numbered_rows'] > 10: quality += 2
        if patterns['aantal_onderdelen'] > 0: quality += 3
        if patterns['nesting'] > 0: quality += 2
        if patterns['controle'] > 0: quality += 1
        
        print(f"   Quality score: {quality}/10")
        patterns['quality'] = quality
        
        return patterns
    
    except Exception as e:
        print(f"   Analysis failed: {e}")
        return {'quality': 0}

def extract_counts_from_excalibur(csv_file: str):
    """Extract exact counts from Excalibur CSV"""
    
    print(f"\n🎯 EXTRACTING COUNTS FROM: {os.path.basename(csv_file)}")
    
    try:
        df = pd.read_csv(csv_file)
        
        # Convert to string for searching
        content = df.to_string().lower()
        
        # Extract NESTING counts from "aantal onderdelen"
        import re
        aantal_matches = re.findall(r'aantal onderdelen[:\s]*(\d+)', content)
        nesting_counts = [int(x) for x in aantal_matches if 5 <= int(x) <= 100]
        
        nesting_total = 0
        if len(nesting_counts) >= 2:
            nesting_total = nesting_counts[0] + nesting_counts[1]
            print(f"   NESTING: {nesting_counts[0]} + {nesting_counts[1]} = {nesting_total}")
        elif len(nesting_counts) == 1:
            nesting_total = nesting_counts[0]
            print(f"   NESTING: {nesting_total}")
        
        # Extract BOERE counts from quality control tables
        boere_count = 0
        for i, row in df.iterrows():
            row_text = ' '.join([str(cell) for cell in row.values]).lower()
            if 'beschrijving' in row_text and 'aantal stuks' in row_text:
                # This is a BOERE table header, count following numbered rows
                for j in range(i+1, min(i+50, len(df))):
                    next_row = df.iloc[j]
                    if str(next_row.iloc[0]).strip().isdigit():
                        next_row_text = ' '.join([str(cell) for cell in next_row.values]).lower()
                        if 'te bestellen' not in next_row_text:
                            boere_count += 1
                break
        
        print(f"   BOERE: {boere_count}")
        
        # Extract ACCURA counts from items with edge processing
        accura_count = 0
        for i, row in df.iterrows():
            if str(row.iloc[0]).strip().isdigit():
                row_text = ' '.join([str(cell) for cell in row.values]).lower()
                if any(indicator in row_text for indicator in ['fineer', 'finger', 'l1', 'l2', 'b1', 'b2', 'standaard']):
                    accura_count += 1
        
        print(f"   ACCURA: {accura_count}")
        
        return {
            'nesting': nesting_total,
            'boere': boere_count,
            'accura': accura_count,
            'method': 'Excalibur Direct'
        }
    
    except Exception as e:
        print(f"   Count extraction failed: {e}")
        return None

if __name__ == "__main__":
    result_file = test_excalibur_direct()
    
    if result_file:
        print(f"\n✅ Excalibur extraction completed!")
        
        # Extract counts
        counts = extract_counts_from_excalibur(result_file)
        
        if counts:
            print(f"\n📊 FINAL COUNTS:")
            print(f"NESTING: {counts['nesting']} (expected 52) {'✅' if counts['nesting'] == 52 else '❌'}")
            print(f"BOERE: {counts['boere']} (expected 62) {'✅' if counts['boere'] == 62 else '❌'}")
            print(f"ACCURA: {counts['accura']} (expected 44) {'✅' if counts['accura'] == 44 else '❌'}")
    else:
        print("\n❌ Excalibur extraction failed")