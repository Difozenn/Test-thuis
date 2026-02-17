#!/usr/bin/env python3
"""
PAGE SCANNER - Find which pages contain which sections
"""

import subprocess
import os
import glob
import shutil

def scan_all_pages(pdf_path: str):
    """Scan all pages to find section locations"""
    
    print(f"🔍 SCANNING ALL PAGES: {os.path.basename(pdf_path)}")
    print("=" * 70)
    
    # Create scan directory
    scan_dir = 'page_scan'
    os.makedirs(scan_dir, exist_ok=True)
    
    # Convert all pages to images
    print("📸 Converting all pages to images...")
    cmd = [
        'pdftoppm',
        '-png',
        '-r', '200',  # Lower resolution for speed
        pdf_path,
        os.path.join(scan_dir, 'scan_page')
    ]
    
    subprocess.run(cmd, capture_output=True)
    
    # Get all page images
    page_images = sorted(glob.glob(os.path.join(scan_dir, 'scan_page-*.png')))
    print(f"✅ Created {len(page_images)} page images")
    
    # OCR each page quickly
    page_analysis = {}
    
    for i, img_path in enumerate(page_images):
        page_num = i + 1
        print(f"🔍 Scanning page {page_num}/{len(page_images)}...")
        
        output_base = img_path.replace('.png', '')
        
        # Quick OCR with PSM 4 (best performer)
        cmd = [
            'tesseract',
            img_path,
            output_base,
            '-l', 'eng',
            '--psm', '4'
        ]
        
        subprocess.run(cmd, capture_output=True)
        
        # Read and analyze
        txt_file = output_base + '.txt'
        if os.path.exists(txt_file):
            with open(txt_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Analyze content
            analysis = analyze_page_content(content, page_num)
            page_analysis[page_num] = analysis
    
    # Print summary
    print("\n📊 PAGE ANALYSIS SUMMARY:")
    print("=" * 70)
    
    for page_num, analysis in page_analysis.items():
        print(f"\n📄 Page {page_num}:")
        print(f"   Sections: {', '.join(analysis['sections']) if analysis['sections'] else 'None'}")
        print(f"   Aantal onderdelen: {analysis['aantal_count']} times")
        print(f"   Numbered items: {analysis['numbered_items']}")
        print(f"   Edge processing: {analysis['edge_items']}")
        
        if analysis['key_content']:
            print(f"   Key content: {analysis['key_content'][:50]}...")
    
    # Find best pages for each section
    print("\n🎯 SECTION LOCATIONS:")
    print("-" * 40)
    
    nesting_pages = [p for p, a in page_analysis.items() if 'Nesting' in a['sections']]
    controle_pages = [p for p, a in page_analysis.items() if 'Controle' in a['sections']]
    magazijn_pages = [p for p, a in page_analysis.items() if 'Magazijn' in a['sections']]
    aantal_pages = [p for p, a in page_analysis.items() if a['aantal_count'] > 0]
    
    print(f"NESTING sections: Pages {nesting_pages}")
    print(f"CONTROLE sections: Pages {controle_pages}")
    print(f"MAGAZIJN sections: Pages {magazijn_pages}")
    print(f"'Aantal onderdelen': Pages {aantal_pages}")
    
    # Cleanup
    shutil.rmtree(scan_dir)
    
    return page_analysis

def analyze_page_content(content: str, page_num: int) -> dict:
    """Analyze page content for key patterns"""
    
    lines = [l.strip() for l in content.split('\n') if l.strip()]
    
    # Find sections
    sections = []
    if any('Nesting' in line for line in lines):
        sections.append('Nesting')
    if any('Controle' in line for line in lines):
        sections.append('Controle')
    if any('Magazijn' in line for line in lines):
        sections.append('Magazijn')
    if any('Opdeelzaag' in line for line in lines):
        sections.append('Opdeelzaag')
    if any('Massief' in line for line in lines):
        sections.append('Massief')
    
    # Count patterns
    aantal_count = sum(1 for line in lines if 'Aantal onderdelen' in line)
    
    # Count numbered items (table rows)
    import re
    numbered_items = len([l for l in lines if re.match(r'^\d+\s+\w+', l)])
    
    # Count edge processing items
    edge_items = len([l for l in lines if 'Fineer' in l or 'Finger' in l or re.search(r'\d+mm', l)])
    
    # Get key content sample
    key_content = ""
    for line in lines[:5]:
        if len(line) > 10:  # Skip short lines
            key_content = line
            break
    
    return {
        'sections': sections,
        'aantal_count': aantal_count,
        'numbered_items': numbered_items,
        'edge_items': edge_items,
        'key_content': key_content,
        'total_lines': len(lines)
    }

def quick_scan_hoekdressing():
    """Quick scan of Hoekdressing PDF"""
    
    pdf_path = 'S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF'
    
    if os.path.exists(pdf_path):
        analysis = scan_all_pages(pdf_path)
        
        print("\n🎯 RECOMMENDATIONS:")
        print("-" * 40)
        
        # Find pages with "Aantal onderdelen"
        aantal_pages = [p for p, a in analysis.items() if a['aantal_count'] > 0]
        if aantal_pages:
            print(f"✅ For NESTING: Use pages {aantal_pages} (contain 'Aantal onderdelen')")
        
        # Find pages with Controle/Magazijn
        section_pages = [p for p, a in analysis.items() if 'Controle' in a['sections'] or 'Magazijn' in a['sections']]
        if section_pages:
            print(f"✅ For BOERE: Use pages {section_pages} (contain Controle/Magazijn)")
        
        # Find pages with most edge processing
        edge_pages = sorted([(p, a['edge_items']) for p, a in analysis.items()], key=lambda x: x[1], reverse=True)[:3]
        if edge_pages:
            print(f"✅ For ACCURA: Use pages {[p for p, _ in edge_pages]} (most edge processing)")
        
    else:
        print(f"❌ PDF not found: {pdf_path}")

if __name__ == "__main__":
    quick_scan_hoekdressing()