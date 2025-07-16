#!/usr/bin/env python3
"""
Try alternative PDF to Excel converters
"""

import pandas as pd
import pdfplumber
import os

def try_camelot_conversion(pdf_path: str):
    """Try camelot-py converter"""
    try:
        import camelot
        print("🔄 Trying Camelot conversion...")
        
        # Extract tables using camelot
        tables = camelot.read_pdf(pdf_path, pages='2-7,11-25', flavor='lattice')
        
        if tables:
            # Save to Excel
            excel_path = 'camelot_tables.xlsx'
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                for i, table in enumerate(tables):
                    table.df.to_excel(writer, sheet_name=f'Table_{i}', index=False)
            
            print(f"✅ Camelot: {len(tables)} tables → {excel_path}")
            return excel_path
        else:
            print("❌ Camelot: No tables found")
            
    except ImportError:
        print("❌ Camelot not installed (pip install camelot-py[cv])")
    except Exception as e:
        print(f"❌ Camelot failed: {e}")
    
    return None

def try_pdfplumber_to_csv(pdf_path: str):
    """Try pdfplumber with CSV export"""
    try:
        print("🔄 Trying pdfplumber → CSV...")
        
        all_tables = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num in [2, 3, 4, 5, 6, 7] + list(range(11, 26)):
                if page_num <= len(pdf.pages):
                    page = pdf.pages[page_num-1]
                    tables = page.extract_tables()
                    
                    for i, table in enumerate(tables):
                        if table and len(table) > 1:
                            # Convert to DataFrame
                            df = pd.DataFrame(table[1:], columns=table[0])
                            all_tables.append((f'Page_{page_num}_Table_{i}', df))
        
        if all_tables:
            # Save each table as CSV
            csv_dir = 'extracted_csvs'
            os.makedirs(csv_dir, exist_ok=True)
            
            for name, df in all_tables:
                csv_path = f'{csv_dir}/{name}.csv'
                df.to_csv(csv_path, index=False)
            
            print(f"✅ PDFplumber: {len(all_tables)} tables → {csv_dir}/")
            return csv_dir
        else:
            print("❌ PDFplumber: No tables found")
            
    except Exception as e:
        print(f"❌ PDFplumber failed: {e}")
    
    return None

def try_pymupdf_conversion(pdf_path: str):
    """Try PyMuPDF (fitz) converter"""
    try:
        import fitz  # PyMuPDF
        print("🔄 Trying PyMuPDF conversion...")
        
        doc = fitz.open(pdf_path)
        all_tables = []
        
        for page_num in [2, 3, 4, 5, 6, 7] + list(range(11, 26)):
            if page_num <= len(doc):
                page = doc[page_num - 1]
                tables = page.find_tables()
                
                for i, table in enumerate(tables):
                    table_data = table.extract()
                    if table_data and len(table_data) > 1:
                        df = pd.DataFrame(table_data[1:], columns=table_data[0])
                        all_tables.append((f'Page_{page_num}_Table_{i}', df))
        
        doc.close()
        
        if all_tables:
            excel_path = 'pymupdf_tables.xlsx'
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                for name, df in all_tables:
                    df.to_excel(writer, sheet_name=name[:31], index=False)  # Excel sheet name limit
            
            print(f"✅ PyMuPDF: {len(all_tables)} tables → {excel_path}")
            return excel_path
        else:
            print("❌ PyMuPDF: No tables found")
            
    except ImportError:
        print("❌ PyMuPDF not installed (pip install PyMuPDF)")
    except Exception as e:
        print(f"❌ PyMuPDF failed: {e}")
    
    return None

def try_pdfminer_text_extraction(pdf_path: str):
    """Try raw text extraction with better parsing"""
    try:
        from pdfminer.high_level import extract_text_to_fp
        from pdfminer.layout import LAParams
        import io
        
        print("🔄 Trying PDFMiner text extraction...")
        
        all_text = {}
        
        with open(pdf_path, 'rb') as file:
            # Extract text with better layout analysis
            laparams = LAParams(
                line_margin=0.5,
                word_margin=0.1,
                char_margin=2.0,
                box_growth=0.5
            )
            
            output_string = io.StringIO()
            extract_text_to_fp(file, output_string, laparams=laparams, 
                             page_numbers=[1, 2, 3, 4, 5, 6] + list(range(10, 25)))
            
            text = output_string.getvalue()
            
            # Save raw text
            with open('pdfminer_text.txt', 'w', encoding='utf-8') as f:
                f.write(text)
            
            print(f"✅ PDFMiner: Raw text → pdfminer_text.txt")
            return 'pdfminer_text.txt'
            
    except ImportError:
        print("❌ PDFMiner not installed (pip install pdfminer.six)")
    except Exception as e:
        print(f"❌ PDFMiner failed: {e}")
    
    return None

if __name__ == "__main__":
    pdf_file = 'S04479_RAPPORT_Rudi Matterne_0411_MO07202-7203_TV-wand (7-7).PDF'
    
    print("🔍 Trying alternative PDF conversion methods...")
    print("="*60)
    
    # Try different converters
    results = []
    
    # 1. Camelot
    camelot_result = try_camelot_conversion(pdf_file)
    if camelot_result:
        results.append(('Camelot', camelot_result))
    
    # 2. PyMuPDF
    pymupdf_result = try_pymupdf_conversion(pdf_file)
    if pymupdf_result:
        results.append(('PyMuPDF', pymupdf_result))
    
    # 3. PDFplumber to CSV
    csv_result = try_pdfplumber_to_csv(pdf_file)
    if csv_result:
        results.append(('PDFplumber CSV', csv_result))
    
    # 4. PDFMiner text
    text_result = try_pdfminer_text_extraction(pdf_file)
    if text_result:
        results.append(('PDFMiner Text', text_result))
    
    print("\n" + "="*60)
    print("🎯 CONVERSION RESULTS:")
    
    if results:
        for method, output in results:
            print(f"✅ {method}: {output}")
        print(f"\n🔍 Check these files to see which gives better quality!")
    else:
        print("❌ All conversion methods failed")
        print("💡 You might need to install additional packages:")
        print("   pip install camelot-py[cv] PyMuPDF pdfminer.six")