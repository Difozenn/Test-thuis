#!/usr/bin/env python3
"""
Convert PDFBox text output to Excel file
"""

import subprocess
import re
import os
import csv

def create_excel_from_pdfbox(pdf_path: str) -> str:
    """Create Excel file from PDFBox text extraction"""
    
    # Use existing PDFBox text file or create new one
    text_file = 'pdfbox_full_text.txt'
    
    if not os.path.exists(text_file):
        print("🔄 Extracting text with PDFBox...")
        cmd = ['java', '-jar', 'pdfbox-app-2.0.28.jar', 'ExtractText', pdf_path, text_file]
        subprocess.run(cmd)
    
    print(f"🔄 Converting {text_file} to Excel format...")
    
    with open(text_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find section boundaries
    nesting_start = None
    controle_start = None
    magazijn_start = None
    
    for i, line in enumerate(lines):
        if 'Nesting' in line and nesting_start is None:
            nesting_start = i
        elif 'Controle' in line and controle_start is None:
            controle_start = i
        elif 'Magazijn' in line and magazijn_start is None:
            magazijn_start = i
            break
    
    # Create CSV files (Excel-compatible)
    excel_base = pdf_path.replace('.PDF', '_pdfbox').replace('.pdf', '_pdfbox')
    
    # NESTING CSV
    nesting_csv = f"{excel_base}_nesting.csv"
    with open(nesting_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Item_Number', 'Onderdeel', 'Lengte', 'Breedte', 'Dikte', 'Materiaal', 'Full_Line'])
        
        if nesting_start and controle_start:
            for line in lines[nesting_start:controle_start]:
                line = line.strip()
                if re.match(r'^\d+\s+', line):
                    parts = line.split()
                    if len(parts) >= 4:
                        writer.writerow([
                            parts[0],
                            parts[1] if len(parts) > 1 else '',
                            parts[2] if len(parts) > 2 else '',
                            parts[3] if len(parts) > 3 else '',
                            parts[4] if len(parts) > 4 else '',
                            parts[5] if len(parts) > 5 else '',
                            line
                        ])
    
    # BOERE CSV
    boere_csv = f"{excel_base}_boere.csv"
    with open(boere_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Numero', 'Full_Line'])
        
        if controle_start and magazijn_start:
            for line in lines[controle_start:magazijn_start]:
                line = line.strip()
                if re.match(r'^\d+', line) and 'te bestellen' not in line.lower():
                    parts = line.split()
                    writer.writerow([parts[0], line])
    
    # ACCURA CSV
    accura_csv = f"{excel_base}_accura.csv"
    with open(accura_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Content', 'Has_L1', 'Has_L2', 'Has_B1', 'Has_B2'])
        
        for line in lines:
            line = line.strip()
            if any(pattern in line for pattern in ['L1', 'L2', 'B1', 'B2']):
                if re.search(r'[LB][12].*\d', line):
                    writer.writerow([
                        line,
                        'L1' in line,
                        'L2' in line,
                        'B1' in line,
                        'B2' in line
                    ])
    
    print(f"✅ Excel files created:")
    print(f"   • {nesting_csv}")
    print(f"   • {boere_csv}")
    print(f"   • {accura_csv}")
    
    # Count items
    nesting_count = sum(1 for line in open(nesting_csv) if line.strip()) - 1  # -1 for header
    boere_count = sum(1 for line in open(boere_csv) if line.strip()) - 1
    accura_count = sum(1 for line in open(accura_csv) if line.strip()) - 1
    
    print(f"📊 Item counts:")
    print(f"   • NESTING: {nesting_count} items")
    print(f"   • BOERE: {boere_count} items")
    print(f"   • ACCURA: {accura_count} items")
    
    return [nesting_csv, boere_csv, accura_csv]

if __name__ == "__main__":
    pdf_file = 'S04479_RAPPORT_Rudi Matterne_0411_MO07202-7203_TV-wand (7-7).PDF'
    
    excel_files = create_excel_from_pdfbox(pdf_file)
    
    print(f"\n🎉 Excel files ready!")
    print(f"Open these in Excel or LibreOffice:")
    for file in excel_files:
        print(f"   • {file}")