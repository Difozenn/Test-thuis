#!/usr/bin/env python3
"""
Debug OCR output to understand the TSV structure
"""

import subprocess
import os
import glob

def debug_ocr_output():
    """Debug what OCR actually produces"""
    
    pdf_path = 'S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF'
    
    print("🔍 DEBUGGING OCR OUTPUT")
    print("=" * 60)
    
    # Convert first page only for debugging
    output_dir = 'debug_ocr'
    os.makedirs(output_dir, exist_ok=True)
    
    print("📸 Converting first page to image...")
    cmd = [
        'pdftoppm',
        '-png',
        '-r', '300',
        '-f', '2',  # Start from page 2 (has data)
        '-l', '2',  # End at page 2
        pdf_path,
        os.path.join(output_dir, 'debug_page')
    ]
    
    subprocess.run(cmd, capture_output=True)
    
    # Get the image
    images = glob.glob(os.path.join(output_dir, 'debug_page-*.png'))
    if not images:
        print("❌ No images created")
        return
    
    img_path = images[0]
    print(f"✅ Created image: {img_path}")
    
    # Run OCR with different modes
    modes = [
        ('6', 'Uniform block of text'),
        ('4', 'Single column text'),
        ('8', 'Single word'),
        ('11', 'Sparse text'),
        ('12', 'Sparse text + OSD')
    ]
    
    for psm, description in modes:
        print(f"\n🔍 Testing PSM {psm}: {description}")
        
        output_base = os.path.join(output_dir, f'debug_psm_{psm}')
        
        # Text output
        cmd = [
            'tesseract',
            img_path,
            output_base + '_txt',
            '-l', 'eng',
            '--psm', psm
        ]
        subprocess.run(cmd, capture_output=True)
        
        # TSV output
        cmd = [
            'tesseract',
            img_path,
            output_base + '_tsv',
            '-l', 'eng',
            '--psm', psm,
            'tsv'
        ]
        subprocess.run(cmd, capture_output=True)
        
        # Check results
        txt_file = output_base + '_txt.txt'
        tsv_file = output_base + '_tsv.tsv'
        
        if os.path.exists(txt_file):
            with open(txt_file, 'r') as f:
                content = f.read().strip()
                lines = [l for l in content.split('\n') if l.strip()]
                print(f"   Text output: {len(lines)} lines")
                if lines:
                    print(f"   Sample: {lines[0][:50]}...")
        
        if os.path.exists(tsv_file):
            with open(tsv_file, 'r') as f:
                tsv_lines = f.readlines()
                print(f"   TSV output: {len(tsv_lines)} lines")
                
                # Show structure
                if len(tsv_lines) > 1:
                    header = tsv_lines[0].strip().split('\t')
                    print(f"   TSV columns: {len(header)}")
                    
                    # Find text in TSV
                    text_items = []
                    for line in tsv_lines[1:6]:  # First 5 data lines
                        parts = line.strip().split('\t')
                        if len(parts) > 11 and parts[11].strip():
                            text_items.append(parts[11])
                    
                    if text_items:
                        print(f"   Sample text items: {text_items[:3]}")

def simple_ocr_test():
    """Simple OCR test on one page"""
    
    print("\n🧪 SIMPLE OCR TEST")
    print("=" * 60)
    
    # Just get text from page 2
    pdf_path = 'S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF'
    
    # Convert page 2
    cmd = [
        'pdftoppm',
        '-png',
        '-r', '300',
        '-f', '2',
        '-l', '2',
        pdf_path,
        'simple_test'
    ]
    subprocess.run(cmd, capture_output=True)
    
    # OCR it
    images = glob.glob('simple_test-*.png')
    if images:
        img = images[0]
        
        cmd = [
            'tesseract',
            img,
            'simple_ocr_result',
            '-l', 'eng'
        ]
        subprocess.run(cmd, capture_output=True)
        
        # Read result
        if os.path.exists('simple_ocr_result.txt'):
            with open('simple_ocr_result.txt', 'r') as f:
                content = f.read()
                
            print("📄 OCR Text from page 2:")
            print("-" * 40)
            lines = content.split('\n')[:20]  # First 20 lines
            for i, line in enumerate(lines):
                if line.strip():
                    print(f"{i+1:2d}: {line}")
            
            # Look for key patterns
            print("\n🔍 Key patterns found:")
            if 'Nesting' in content:
                print("✅ Found 'Nesting'")
            if 'Aantal onderdelen' in content:
                count = content.count('Aantal onderdelen')
                print(f"✅ Found 'Aantal onderdelen' {count} times")
            if re.search(r'\d+\s+\w+.*\d+.*\d+', content):
                print("✅ Found numbered table rows")
        
        # Cleanup
        for f in glob.glob('simple_test-*.png'):
            os.remove(f)
        if os.path.exists('simple_ocr_result.txt'):
            os.remove('simple_ocr_result.txt')

if __name__ == "__main__":
    debug_ocr_output()
    simple_ocr_test()