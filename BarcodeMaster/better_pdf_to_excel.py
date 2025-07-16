#!/usr/bin/env python3
"""
BETTER PDF TO EXCEL CONVERTER
Using alternative methods for better table extraction
"""

import subprocess
import os
import requests
import json

def convert_with_pdfplumber_to_csv(pdf_path: str) -> str:
    """Convert PDF to CSV using pdfplumber for better table detection"""
    
    print("🔄 Converting with pdfplumber to CSV...")
    
    try:
        import pdfplumber
        import pandas as pd
        
        csv_file = pdf_path.replace('.PDF', '_pdfplumber.csv').replace('.pdf', '_pdfplumber.csv')
        
        all_tables = []
        
        with pdfplumber.open(pdf_path) as pdf:
            print(f"   Processing {len(pdf.pages)} pages...")
            
            for page_num, page in enumerate(pdf.pages):
                print(f"   Page {page_num + 1}...")
                
                # Extract tables from this page
                tables = page.extract_tables()
                
                for table_num, table in enumerate(tables):
                    if table and len(table) > 1:  # Skip empty tables
                        # Convert to DataFrame
                        df = pd.DataFrame(table[1:], columns=table[0])
                        # Add metadata
                        df['_page'] = page_num + 1
                        df['_table'] = table_num + 1
                        all_tables.append(df)
        
        if all_tables:
            # Combine all tables
            combined_df = pd.concat(all_tables, ignore_index=True, sort=False)
            combined_df.to_csv(csv_file, index=False)
            
            print(f"✅ PDFPlumber conversion successful: {csv_file}")
            print(f"   Extracted {len(all_tables)} tables, {len(combined_df)} total rows")
            return csv_file
        
    except ImportError:
        print("   PDFPlumber not available")
    except Exception as e:
        print(f"   PDFPlumber failed: {e}")
    
    return None

def convert_with_pymupdf(pdf_path: str) -> str:
    """Convert PDF using PyMuPDF (fitz) for text extraction"""
    
    print("🔄 Converting with PyMuPDF...")
    
    try:
        import fitz  # PyMuPDF
        import pandas as pd
        
        csv_file = pdf_path.replace('.PDF', '_pymupdf.csv').replace('.pdf', '_pymupdf.csv')
        
        doc = fitz.open(pdf_path)
        all_text_data = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Get text with layout preservation
            text = page.get_text("dict")
            
            # Extract tables from text blocks
            for block in text["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        line_text = ""
                        for span in line["spans"]:
                            line_text += span["text"] + " "
                        
                        if line_text.strip():
                            # Split by multiple spaces to detect columns
                            parts = [p.strip() for p in line_text.split() if p.strip()]
                            if len(parts) > 2:  # Likely a table row
                                row_data = {f'col_{i}': part for i, part in enumerate(parts)}
                                row_data['_page'] = page_num + 1
                                all_text_data.append(row_data)
        
        if all_text_data:
            df = pd.DataFrame(all_text_data)
            df.to_csv(csv_file, index=False)
            
            print(f"✅ PyMuPDF conversion successful: {csv_file}")
            print(f"   Extracted {len(all_text_data)} rows")
            return csv_file
        
    except ImportError:
        print("   PyMuPDF not available")
    except Exception as e:
        print(f"   PyMuPDF failed: {e}")
    
    return None

def convert_with_pdf2txt_and_parse(pdf_path: str) -> str:
    """Convert PDF to text and parse into structured data"""
    
    print("🔄 Converting with pdf2txt + parsing...")
    
    try:
        from pdfminer.high_level import extract_text
        import pandas as pd
        import re
        
        csv_file = pdf_path.replace('.PDF', '_parsed.csv').replace('.pdf', '_parsed.csv')
        
        # Extract text
        text = extract_text(pdf_path)
        lines = text.split('\n')
        
        # Parse into structured data
        structured_data = []
        current_page = 1
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect page breaks
            if 'Page' in line and 'of' in line:
                try:
                    current_page = int(re.search(r'Page (\d+)', line).group(1))
                except:
                    pass
                continue
            
            # Detect table rows (start with number)
            if re.match(r'^\d+\s+\w+', line):
                # Split into columns
                parts = re.split(r'\s{2,}', line)  # Split on 2+ spaces
                if len(parts) >= 3:
                    row_data = {f'col_{i}': part for i, part in enumerate(parts)}
                    row_data['_page'] = current_page
                    row_data['_raw_line'] = line
                    structured_data.append(row_data)
        
        if structured_data:
            df = pd.DataFrame(structured_data)
            df.to_csv(csv_file, index=False)
            
            print(f"✅ Parsed conversion successful: {csv_file}")
            print(f"   Extracted {len(structured_data)} structured rows")
            return csv_file
        
    except ImportError:
        print("   PDFMiner not available")
    except Exception as e:
        print(f"   Parsing failed: {e}")
    
    return None

def convert_with_camelot_lattice(pdf_path: str) -> str:
    """Convert using Camelot with lattice mode for better table detection"""
    
    print("🔄 Converting with Camelot (lattice mode)...")
    
    try:
        import camelot
        import pandas as pd
        
        csv_file = pdf_path.replace('.PDF', '_camelot.csv').replace('.pdf', '_camelot.csv')
        
        # Use lattice mode for PDFs with table borders
        tables = camelot.read_pdf(pdf_path, flavor='lattice', pages='all')
        
        if tables:
            all_tables = []
            for i, table in enumerate(tables):
                df = table.df
                df['_table_num'] = i + 1
                df['_page'] = table.parsing_report['page']
                all_tables.append(df)
            
            combined_df = pd.concat(all_tables, ignore_index=True)
            combined_df.to_csv(csv_file, index=False)
            
            print(f"✅ Camelot conversion successful: {csv_file}")
            print(f"   Extracted {len(tables)} tables, {len(combined_df)} total rows")
            return csv_file
        
    except ImportError:
        print("   Camelot not available")
    except Exception as e:
        print(f"   Camelot failed: {e}")
    
    return None

def analyze_csv_quality(csv_file: str) -> dict:
    """Analyze the quality of CSV conversion"""
    
    if not os.path.exists(csv_file):
        return {'quality': 0, 'reason': 'File not found'}
    
    try:
        import pandas as pd
        
        df = pd.read_csv(csv_file)
        
        # Quality metrics
        total_rows = len(df)
        total_cols = len(df.columns)
        non_empty_cells = df.count().sum()
        
        # Check for key patterns
        text_content = df.to_string().lower()
        has_nesting = 'nesting' in text_content
        has_aantal = 'aantal onderdelen' in text_content
        has_controle = 'controle' in text_content
        has_fineer = 'fineer' in text_content
        has_numbers = any(df[col].dtype in ['int64', 'float64'] for col in df.columns)
        
        # Quality scoring
        quality = 0
        if total_rows > 50:
            quality += 3
        if total_cols > 5:
            quality += 2
        if has_aantal:
            quality += 3
        if has_nesting:
            quality += 2
        if has_controle:
            quality += 2
        if has_fineer:
            quality += 2
        if has_numbers:
            quality += 1
        
        return {
            'quality': quality,
            'rows': total_rows,
            'cols': total_cols,
            'non_empty_cells': non_empty_cells,
            'has_nesting': has_nesting,
            'has_aantal': has_aantal,
            'has_controle': has_controle,
            'has_fineer': has_fineer
        }
    
    except Exception as e:
        return {'quality': 0, 'reason': str(e)}

def find_best_pdf_conversion(pdf_path: str) -> str:
    """Try multiple conversion methods and return the best result"""
    
    print(f"🎯 TESTING BETTER PDF TO EXCEL/CSV METHODS")
    print(f"PDF: {os.path.basename(pdf_path)}")
    print("=" * 70)
    
    conversion_methods = [
        ('PDFPlumber to CSV', convert_with_pdfplumber_to_csv),
        ('Camelot Lattice', convert_with_camelot_lattice),
        ('PyMuPDF', convert_with_pymupdf),
        ('PDF2TXT + Parse', convert_with_pdf2txt_and_parse)
    ]
    
    best_file = None
    best_quality = 0
    results = []
    
    for method_name, method_func in conversion_methods:
        print(f"\n📊 Testing {method_name}...")
        
        try:
            result_file = method_func(pdf_path)
            
            if result_file:
                quality = analyze_csv_quality(result_file)
                results.append({
                    'method': method_name,
                    'file': result_file,
                    'quality': quality
                })
                
                print(f"   Quality score: {quality['quality']}/15")
                print(f"   Rows: {quality.get('rows', 0)}, Cols: {quality.get('cols', 0)}")
                print(f"   Has key patterns: Aantal={quality.get('has_aantal', False)}, "
                      f"Nesting={quality.get('has_nesting', False)}, "
                      f"Controle={quality.get('has_controle', False)}")
                
                if quality['quality'] > best_quality:
                    best_quality = quality['quality']
                    best_file = result_file
        
        except Exception as e:
            print(f"   ❌ {method_name} failed: {e}")
    
    print(f"\n🏆 BEST CONVERSION:")
    if best_file:
        best_result = next(r for r in results if r['file'] == best_file)
        print(f"Method: {best_result['method']}")
        print(f"File: {best_file}")
        print(f"Quality: {best_quality}/15")
        return best_file
    else:
        print("❌ No successful conversions")
        return None

def test_better_conversion():
    """Test better PDF conversion methods"""
    
    pdf_path = 'S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF'
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print("Expected: NESTING=52, BOERE=62, ACCURA=44")
    print("-" * 70)
    
    # Find best conversion
    best_file = find_best_pdf_conversion(pdf_path)
    
    if best_file:
        print(f"\n✅ Best conversion saved to: {best_file}")
        print("You can now analyze this file to extract the exact counts.")
    else:
        print("❌ All conversion methods failed")

if __name__ == "__main__":
    test_better_conversion()