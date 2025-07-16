#!/usr/bin/env python3
"""
Convert PDFBox HTML output to structured Excel - the non-Python solution approach
"""

import subprocess
import os
import re
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path

def extract_pdf_with_pdfbox(pdf_path: str) -> str:
    """Extract PDF using PDFBox Java library"""
    
    html_output = pdf_path.replace('.PDF', '_pdfbox.html').replace('.pdf', '_pdfbox.html')
    
    print(f"🔄 Extracting {pdf_path} using PDFBox...")
    
    # Run PDFBox extraction
    cmd = [
        'java', '-jar', 'pdfbox-app-2.0.28.jar', 
        'ExtractText', '-html', pdf_path, html_output
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ PDFBox extraction failed: {result.stderr}")
        return None
    
    print(f"✅ PDFBox extraction complete: {html_output}")
    return html_output

def parse_pdfbox_html_to_excel(html_path: str) -> str:
    """Parse PDFBox HTML output and convert to structured Excel"""
    
    print(f"🔄 Parsing HTML to structured Excel...")
    
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract all text content
    pages = soup.find_all('div', style=lambda x: x and 'page-break' in x)
    
    # Data structures for each user type
    nesting_data = []
    boere_data = []
    accura_data = []
    
    current_section = None
    
    for page in pages:
        paragraphs = page.find_all('p')
        
        for p in paragraphs:
            text = p.get_text().strip()
            
            # Section detection
            if 'Nesting' in text:
                current_section = 'nesting'
                continue
            elif 'Opdeelzaag' in text:
                current_section = 'opdeelzaag'  # Part of nesting
                continue
            elif 'Controle' in text:
                current_section = 'boere'
                continue
            elif 'Magazijn' in text:
                current_section = None  # End of boere section
                continue
            elif 'Accura' in text:
                current_section = 'accura'
                continue
            
            # Parse data based on current section
            if current_section in ['nesting', 'opdeelzaag']:
                # Look for table-like data
                if re.match(r'\d+', text):  # Starts with number
                    parts = text.split()
                    if len(parts) >= 6:  # Has enough columns
                        nesting_data.append({
                            'item_number': parts[0],
                            'onderdeel': parts[1] if len(parts) > 1 else '',
                            'materiaal': parts[2] if len(parts) > 2 else '',
                            'lengte': parts[3] if len(parts) > 3 else '',
                            'breedte': parts[4] if len(parts) > 4 else '',
                            'dikte': parts[5] if len(parts) > 5 else '',
                            'section': current_section
                        })
            
            elif current_section == 'boere':
                # Look for N° entries
                if 'N°' in text or re.match(r'\d+', text):
                    # Skip "Te bestellen" entries
                    if 'Te bestellen' not in text and 'TE BESTELLEN' not in text:
                        parts = text.split()
                        if parts and parts[0].isdigit():
                            boere_data.append({
                                'numero': parts[0],
                                'content': text
                            })
            
            elif current_section == 'accura':
                # Look for L1/L2/B1/B2 data
                if any(x in text for x in ['L1', 'L2', 'B1', 'B2']):
                    accura_data.append({
                        'content': text,
                        'has_l1': 'L1' in text,
                        'has_l2': 'L2' in text,
                        'has_b1': 'B1' in text,
                        'has_b2': 'B2' in text
                    })
    
    # Create Excel file with multiple sheets
    excel_output = html_path.replace('.html', '_structured.xlsx')
    
    with pd.ExcelWriter(excel_output, engine='openpyxl') as writer:
        
        # Nesting sheet
        if nesting_data:
            df_nesting = pd.DataFrame(nesting_data)
            df_nesting.to_excel(writer, sheet_name='Nesting', index=False)
        
        # Boere sheet  
        if boere_data:
            df_boere = pd.DataFrame(boere_data)
            df_boere.to_excel(writer, sheet_name='Boere', index=False)
        
        # Accura sheet
        if accura_data:
            df_accura = pd.DataFrame(accura_data)
            df_accura.to_excel(writer, sheet_name='Accura', index=False)
    
    print(f"✅ Structured Excel created: {excel_output}")
    print(f"📊 Results:")
    print(f"   • NESTING: {len(nesting_data)} items")
    print(f"   • BOERE: {len(boere_data)} items")  
    print(f"   • ACCURA: {len(accura_data)} items")
    
    return excel_output

def full_pdfbox_conversion(pdf_path: str) -> str:
    """Complete PDF to Excel conversion using PDFBox"""
    
    print(f"🚀 Starting PDFBox PDF-to-Excel conversion...")
    
    # Step 1: Extract with PDFBox
    html_path = extract_pdf_with_pdfbox(pdf_path)
    if not html_path:
        return None
    
    # Step 2: Parse HTML to Excel
    excel_path = parse_pdfbox_html_to_excel(html_path)
    
    print(f"🎯 Conversion complete: {excel_path}")
    return excel_path

if __name__ == "__main__":
    pdf_file = 'S04479_RAPPORT_Rudi Matterne_0411_MO07202-7203_TV-wand (7-7).PDF'
    
    if not os.path.exists(pdf_file):
        print(f"❌ PDF file not found: {pdf_file}")
        exit(1)
    
    result = full_pdfbox_conversion(pdf_file)
    
    if result:
        print(f"\n🎉 SUCCESS! Excel file ready: {result}")
        print(f"This is the non-Python approach working!")
    else:
        print(f"\n❌ Conversion failed")