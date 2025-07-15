#!/usr/bin/env python3
"""
Simple PDF test using PyPDF2 that should be available
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import PyPDF2
    pdf_available = True
except ImportError:
    pdf_available = False

def test_pdf_structure(pdf_path):
    """Test PDF structure with basic PyPDF2."""
    print(f"\nTesting PDF structure: {pdf_path}")
    
    if not pdf_available:
        print("ERROR: PyPDF2 not available")
        return
    
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            print(f"Number of pages: {len(pdf_reader.pages)}")
            
            for page_num, page in enumerate(pdf_reader.pages, 1):
                print(f"\n=== Page {page_num} ===")
                text = page.extract_text()
                print(f"Text length: {len(text)} characters")
                
                # Look for ACCURA markers
                accura_indicators = ['L1', 'L2', 'B1', 'B2']
                found_accura = [indicator for indicator in accura_indicators if indicator in text.upper()]
                print(f"ACCURA indicators found: {found_accura}")
                
                # Look for BOERE markers
                boere_indicators = ['CONTROLE', 'PRO.METHODE', 'METHODE']
                found_boere = [indicator for indicator in boere_indicators if indicator.upper() in text.upper()]
                print(f"BOERE indicators found: {found_boere}")
                
                # Show first 500 characters
                print(f"First 500 chars: {text[:500]}...")
                
                # Look for table-like structure
                lines = text.split('\n')
                table_lines = [line for line in lines if len(line.split()) > 3]  # Lines with multiple columns
                print(f"Potential table lines: {len(table_lines)}")
                
                if table_lines:
                    print("Sample table lines:")
                    for i, line in enumerate(table_lines[:5]):  # Show first 5
                        print(f"  {i+1}: {line}")
                
    except Exception as e:
        print(f"Error reading PDF: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    pdf_path = "/home/difusion/Projects/BarcodeMaster/S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF"
    
    print("Simple PDF Structure Test")
    print("========================")
    
    if not os.path.exists(pdf_path):
        print(f"ERROR: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    test_pdf_structure(pdf_path)