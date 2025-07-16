#!/usr/bin/env python3
"""
PDFBox-based parser - the fully automatic functional solution
Uses Java PDFBox for extraction, Python for precise parsing
"""

import subprocess
import re
import os

def extract_with_pdfbox(pdf_path: str) -> str:
    """Extract PDF text using PDFBox Java library"""
    
    text_output = pdf_path.replace('.PDF', '_pdfbox.txt').replace('.pdf', '_pdfbox.txt')
    
    print(f"🔄 Extracting text using PDFBox...")
    
    cmd = ['java', '-jar', 'pdfbox-app-2.0.28.jar', 'ExtractText', pdf_path, text_output]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ PDFBox extraction failed: {result.stderr}")
        return None
    
    print(f"✅ PDFBox extraction complete: {text_output}")
    return text_output

def parse_pdfbox_text(text_file: str) -> dict:
    """Parse PDFBox extracted text for precise counts"""
    
    print(f"🔄 Parsing extracted text for precise counts...")
    
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
    
    print(f"📍 Section boundaries: Nesting={nesting_start}, Controle={controle_start}, Magazijn={magazijn_start}")
    
    results = {
        'nesting': {'items': [], 'total_count': 0},
        'boere': {'items': [], 'boere_count': 0},
        'accura': {'items': [], 'accura_items': 0}
    }
    
    # Parse NESTING section (nesting_start to controle_start)
    if nesting_start is not None and controle_start is not None:
        nesting_lines = lines[nesting_start:controle_start]
        
        for line in nesting_lines:
            line = line.strip()
            # Look for numbered items
            if re.match(r'^\d+\s+', line):
                parts = line.split()
                if len(parts) >= 6:  # Has basic columns
                    item = {
                        'item_number': parts[0],
                        'onderdeel': parts[1] if len(parts) > 1 else '',
                        'lengte': parts[2] if len(parts) > 2 else '',
                        'breedte': parts[3] if len(parts) > 3 else '',
                        'dikte': parts[4] if len(parts) > 4 else '',
                        'materiaal': parts[5] if len(parts) > 5 else ''
                    }
                    results['nesting']['items'].append(item)
        
        results['nesting']['total_count'] = len(results['nesting']['items'])
    
    # Parse BOERE section (controle_start to magazijn_start)
    if controle_start is not None and magazijn_start is not None:
        boere_lines = lines[controle_start:magazijn_start]
        
        for line in boere_lines:
            line = line.strip()
            # Look for numbered items, exclude "Te bestellen"
            if re.match(r'^\d+', line) and 'te bestellen' not in line.lower():
                results['boere']['items'].append({
                    'numero': line.split()[0],
                    'content': line
                })
        
        results['boere']['boere_count'] = len(results['boere']['items'])
    
    # Parse ACCURA section (look for L1/L2/B1/B2 patterns)
    for line in lines:
        line = line.strip()
        # Look for lines with L1/L2/B1/B2 data
        if any(pattern in line for pattern in ['L1', 'L2', 'B1', 'B2']):
            # Make sure it's actual data, not just headers
            if re.search(r'[LB][12].*\d', line):
                results['accura']['items'].append({
                    'content': line,
                    'has_l1': 'L1' in line,
                    'has_l2': 'L2' in line,
                    'has_b1': 'B1' in line,
                    'has_b2': 'B2' in line
                })
    
    results['accura']['accura_items'] = len(results['accura']['items'])
    
    print(f"📊 Parsing results:")
    print(f"   • NESTING: {results['nesting']['total_count']} items")
    print(f"   • BOERE: {results['boere']['boere_count']} items")
    print(f"   • ACCURA: {results['accura']['accura_items']} items")
    
    return results

def pdfbox_full_extraction(pdf_path: str) -> dict:
    """Complete PDF extraction and parsing using PDFBox"""
    
    print(f"🚀 Starting PDFBox-based extraction for {pdf_path}")
    
    # Step 1: Extract text with PDFBox
    text_file = extract_with_pdfbox(pdf_path)
    if not text_file:
        return None
    
    # Step 2: Parse the extracted text
    results = parse_pdfbox_text(text_file)
    
    print(f"🎯 PDFBox extraction complete!")
    return results

# Integration functions for background_import_service.py
def get_nesting_count_pdfbox(pdf_path: str) -> int:
    """Get NESTING count using PDFBox extraction"""
    results = pdfbox_full_extraction(pdf_path)
    return results['nesting']['total_count'] if results else 0

def get_boere_count_pdfbox(pdf_path: str) -> int:
    """Get BOERE count using PDFBox extraction"""
    results = pdfbox_full_extraction(pdf_path)
    return results['boere']['boere_count'] if results else 0

def get_accura_count_pdfbox(pdf_path: str) -> int:
    """Get ACCURA count using PDFBox extraction"""
    results = pdfbox_full_extraction(pdf_path)
    return results['accura']['accura_items'] if results else 0

if __name__ == "__main__":
    pdf_file = 'S04479_RAPPORT_Rudi Matterne_0411_MO07202-7203_TV-wand (7-7).PDF'
    
    if not os.path.exists(pdf_file):
        print(f"❌ PDF file not found: {pdf_file}")
        exit(1)
    
    results = pdfbox_full_extraction(pdf_file)
    
    if results:
        print(f"\n🎉 PDFBOX EXTRACTION RESULTS:")
        print(f"• NESTING: {results['nesting']['total_count']} items")
        print(f"• BOERE: {results['boere']['boere_count']} items")
        print(f"• ACCURA: {results['accura']['accura_items']} items")
        print(f"\n💡 This is the fully automatic functional solution!")
        print(f"Using Java PDFBox + Python parsing = Perfect extraction")
    else:
        print(f"\n❌ Extraction failed")