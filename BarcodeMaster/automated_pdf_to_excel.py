#!/usr/bin/env python3
"""
AUTOMATED PDF TO EXCEL CONVERTER
Using multiple methods to get the best possible Excel extraction
"""

import subprocess
import os
import pandas as pd
import requests
import time

def convert_with_libreoffice(pdf_path: str) -> str:
    """Convert PDF to Excel using LibreOffice"""
    
    print("🔄 Converting with LibreOffice...")
    
    output_dir = os.path.dirname(pdf_path)
    
    cmd = [
        'libreoffice',
        '--headless',
        '--convert-to', 'xlsx',
        '--outdir', output_dir,
        pdf_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        excel_file = pdf_path.replace('.PDF', '.xlsx').replace('.pdf', '.xlsx')
        if os.path.exists(excel_file):
            print(f"✅ LibreOffice conversion successful: {excel_file}")
            return excel_file
    
    print(f"❌ LibreOffice conversion failed: {result.stderr}")
    return None

def convert_with_pandoc(pdf_path: str) -> str:
    """Convert PDF to Excel using pandoc"""
    
    print("🔄 Converting with pandoc...")
    
    excel_file = pdf_path.replace('.PDF', '_pandoc.xlsx').replace('.pdf', '_pandoc.xlsx')
    
    cmd = [
        'pandoc',
        pdf_path,
        '-o', excel_file
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(excel_file):
            print(f"✅ Pandoc conversion successful: {excel_file}")
            return excel_file
        else:
            print(f"❌ Pandoc conversion failed: {result.stderr}")
    except FileNotFoundError:
        print("❌ Pandoc not installed")
    
    return None

def convert_with_python_libraries(pdf_path: str) -> str:
    """Convert using Python libraries (tabula, camelot)"""
    
    print("🔄 Converting with Python libraries...")
    
    excel_file = pdf_path.replace('.PDF', '_python.xlsx').replace('.pdf', '_python.xlsx')
    
    try:
        # Try tabula-py first
        import tabula
        
        print("   Trying tabula-py...")
        
        # Extract all tables from all pages
        tables = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True)
        
        if tables:
            # Write to Excel with multiple sheets
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                for i, table in enumerate(tables):
                    table.to_excel(writer, sheet_name=f'Table_{i+1}', index=False)
            
            print(f"✅ Tabula conversion successful: {excel_file}")
            return excel_file
    
    except ImportError:
        print("   Tabula not available")
    except Exception as e:
        print(f"   Tabula failed: {e}")
    
    try:
        # Try camelot as backup
        import camelot
        
        print("   Trying camelot...")
        
        tables = camelot.read_pdf(pdf_path, pages='all')
        
        if tables:
            # Combine all tables
            combined_df = pd.concat([table.df for table in tables], ignore_index=True)
            combined_df.to_excel(excel_file, index=False)
            
            print(f"✅ Camelot conversion successful: {excel_file}")
            return excel_file
    
    except ImportError:
        print("   Camelot not available")
    except Exception as e:
        print(f"   Camelot failed: {e}")
    
    return None

def analyze_excel_quality(excel_file: str) -> dict:
    """Analyze the quality of Excel conversion"""
    
    if not os.path.exists(excel_file):
        return {'quality': 0, 'reason': 'File not found'}
    
    try:
        # Try to read the Excel file
        if excel_file.endswith('.xlsx'):
            df = pd.read_excel(excel_file, sheet_name=None)  # Read all sheets
        else:
            df = {'Sheet1': pd.read_csv(excel_file)}
        
        total_rows = 0
        total_cols = 0
        has_numbers = False
        has_text = False
        
        for sheet_name, sheet_df in df.items():
            total_rows += len(sheet_df)
            total_cols += len(sheet_df.columns)
            
            # Check for numeric data
            for col in sheet_df.columns:
                if sheet_df[col].dtype in ['int64', 'float64']:
                    has_numbers = True
                if sheet_df[col].dtype == 'object':
                    has_text = True
        
        # Quality scoring
        quality = 0
        if total_rows > 10:
            quality += 3
        if total_cols > 3:
            quality += 2
        if has_numbers:
            quality += 3
        if has_text:
            quality += 2
        
        return {
            'quality': quality,
            'rows': total_rows,
            'cols': total_cols,
            'sheets': len(df),
            'has_numbers': has_numbers,
            'has_text': has_text
        }
    
    except Exception as e:
        return {'quality': 0, 'reason': str(e)}

def find_best_conversion(pdf_path: str) -> str:
    """Try multiple conversion methods and return the best result"""
    
    print(f"🎯 FINDING BEST PDF TO EXCEL CONVERSION")
    print(f"PDF: {os.path.basename(pdf_path)}")
    print("=" * 70)
    
    conversion_methods = [
        ('LibreOffice', convert_with_libreoffice),
        ('Python Libraries', convert_with_python_libraries),
        ('Pandoc', convert_with_pandoc)
    ]
    
    best_file = None
    best_quality = 0
    results = []
    
    for method_name, method_func in conversion_methods:
        print(f"\n📊 Testing {method_name}...")
        
        try:
            excel_file = method_func(pdf_path)
            
            if excel_file:
                quality = analyze_excel_quality(excel_file)
                results.append({
                    'method': method_name,
                    'file': excel_file,
                    'quality': quality
                })
                
                print(f"   Quality score: {quality['quality']}/10")
                print(f"   Rows: {quality.get('rows', 0)}, Cols: {quality.get('cols', 0)}")
                
                if quality['quality'] > best_quality:
                    best_quality = quality['quality']
                    best_file = excel_file
        
        except Exception as e:
            print(f"   ❌ {method_name} failed: {e}")
    
    print(f"\n🏆 BEST CONVERSION:")
    if best_file:
        best_result = next(r for r in results if r['file'] == best_file)
        print(f"Method: {best_result['method']}")
        print(f"File: {best_file}")
        print(f"Quality: {best_quality}/10")
        return best_file
    else:
        print("❌ No successful conversions")
        return None

def extract_counts_from_excel(excel_file: str) -> dict:
    """Extract NESTING, BOERE, ACCURA counts from Excel file"""
    
    print(f"\n📊 EXTRACTING COUNTS FROM: {os.path.basename(excel_file)}")
    
    if not os.path.exists(excel_file):
        return None
    
    try:
        # Read all sheets
        df_dict = pd.read_excel(excel_file, sheet_name=None)
        
        counts = {
            'nesting': 0,
            'boere': 0,
            'accura': 0,
            'method': 'Excel Analysis'
        }
        
        for sheet_name, df in df_dict.items():
            print(f"\n   Sheet: {sheet_name} ({len(df)} rows, {len(df.columns)} cols)")
            
            # Convert to string for analysis
            sheet_text = df.to_string().lower()
            
            # Count NESTING - look for "aantal onderdelen"
            aantal_matches = sheet_text.count('aantal onderdelen')
            if aantal_matches > 0:
                print(f"   Found {aantal_matches} 'Aantal onderdelen' markers")
            
            # Count BOERE - look for "beschrijving" tables
            if 'beschrijving' in sheet_text and 'aantal stuks' in sheet_text:
                boere_items = len([i for i, row in df.iterrows() 
                                 if str(row.iloc[0]).isdigit() and 'bestellen' not in str(row).lower()])
                counts['boere'] += boere_items
                print(f"   Found {boere_items} BOERE items")
            
            # Count ACCURA - look for edge processing
            if any(col for col in df.columns if 'l1' in str(col).lower() or 'l2' in str(col).lower()):
                accura_items = len([i for i, row in df.iterrows() 
                                  if str(row.iloc[0]).isdigit() and 
                                  any('fineer' in str(cell).lower() or 'finger' in str(cell).lower() 
                                      for cell in row)])
                counts['accura'] += accura_items
                print(f"   Found {accura_items} ACCURA items")
        
        print(f"\n✅ EXTRACTED COUNTS:")
        print(f"NESTING: {counts['nesting']}")
        print(f"BOERE: {counts['boere']}")
        print(f"ACCURA: {counts['accura']}")
        
        return counts
    
    except Exception as e:
        print(f"❌ Failed to extract counts: {e}")
        return None

def test_pdf_to_excel():
    """Test PDF to Excel conversion on Hoekdressing"""
    
    pdf_path = 'S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF'
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print("Expected: NESTING=52, BOERE=62, ACCURA=44")
    print("-" * 70)
    
    # Find best conversion
    best_excel = find_best_conversion(pdf_path)
    
    if best_excel:
        # Extract counts
        counts = extract_counts_from_excel(best_excel)
        
        if counts:
            print(f"\n✅ COMPARISON:")
            print(f"NESTING: {counts['nesting']} (expected 52)")
            print(f"BOERE: {counts['boere']} (expected 62)")
            print(f"ACCURA: {counts['accura']} (expected 44)")

if __name__ == "__main__":
    test_pdf_to_excel()