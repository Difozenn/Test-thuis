#!/usr/bin/env python3
"""
VISUAL OCR DEBUGGER
Shows exactly what happens during OCR processing with visual feedback
"""

import subprocess
import os
import re
import glob
import shutil

def create_visual_ocr_debug(pdf_path: str, page_num: int = 2):
    """Create a visual debug of OCR processing for a specific page"""
    
    print(f"🔍 VISUAL OCR DEBUG FOR PAGE {page_num}")
    print("=" * 70)
    
    # Create debug directory
    debug_dir = 'ocr_debug_visual'
    os.makedirs(debug_dir, exist_ok=True)
    
    # Step 1: Convert PDF page to image
    print(f"📸 Step 1: Converting PDF page {page_num} to image...")
    
    cmd = [
        'pdftoppm',
        '-png',
        '-r', '300',
        '-f', str(page_num),
        '-l', str(page_num),
        pdf_path,
        os.path.join(debug_dir, 'original_page')
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Failed to convert PDF: {result.stderr}")
        return
    
    # Find the created image
    images = glob.glob(os.path.join(debug_dir, 'original_page-*.png'))
    if not images:
        print("❌ No image created")
        return
    
    img_path = images[0]
    print(f"✅ Created image: {os.path.basename(img_path)}")
    
    # Step 2: Run OCR with different modes and outputs
    print("\n🔍 Step 2: Running OCR with multiple output formats...")
    
    ocr_modes = [
        ('txt', 'Plain text output'),
        ('tsv', 'Tab-separated values with coordinates'),
        ('hocr', 'HTML with word positions'),
        ('pdf', 'Searchable PDF overlay')
    ]
    
    psm_modes = [
        ('6', 'Uniform block of text'),
        ('4', 'Single column text'),
        ('11', 'Sparse text')
    ]
    
    results = {}
    
    for output_format, format_desc in ocr_modes:
        print(f"\n   📄 {format_desc}...")
        
        for psm, psm_desc in psm_modes:
            output_name = f"ocr_psm{psm}_{output_format}"
            output_path = os.path.join(debug_dir, output_name)
            
            cmd = [
                'tesseract',
                img_path,
                output_path,
                '-l', 'eng+nld',
                '--psm', psm,
                output_format
            ]
            
            subprocess.run(cmd, capture_output=True)
            
            # Read and analyze result
            result_file = f"{output_path}.{output_format}"
            if os.path.exists(result_file):
                try:
                    with open(result_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    # Try with different encoding for PDF files
                    try:
                        with open(result_file, 'rb') as f:
                            content = f"[Binary file: {len(f.read())} bytes]"
                    except:
                        content = "[Could not read file]"
                
                results[f"PSM{psm}_{output_format}"] = {
                    'content': content,
                    'file': result_file,
                    'description': f"PSM {psm} ({psm_desc}) - {format_desc}"
                }
    
    # Step 3: Analyze and display results
    print("\n📊 Step 3: Analyzing OCR results...")
    display_ocr_analysis(results, debug_dir)
    
    # Step 4: Test our parsing logic
    print("\n🧪 Step 4: Testing parsing logic on OCR output...")
    test_parsing_on_ocr(results)
    
    print(f"\n📁 All debug files saved in: {debug_dir}/")
    print("   - Original image: original_page-*.png")
    print("   - OCR outputs: ocr_psm*_*")
    print("   - Analysis: ocr_analysis.txt")

def display_ocr_analysis(results: dict, debug_dir: str):
    """Display detailed analysis of OCR results"""
    
    analysis_file = os.path.join(debug_dir, 'ocr_analysis.txt')
    
    with open(analysis_file, 'w', encoding='utf-8') as f:
        f.write("OCR ANALYSIS REPORT\n")
        f.write("=" * 50 + "\n\n")
        
        for key, result in results.items():
            f.write(f"{result['description']}\n")
            f.write("-" * 40 + "\n")
            
            content = result['content']
            lines = [l for l in content.split('\n') if l.strip()]
            
            f.write(f"Total lines extracted: {len(lines)}\n")
            
            # Count key patterns
            nesting_count = content.count('Nesting')
            aantal_count = content.count('Aantal onderdelen')
            controle_count = content.count('Controle')
            magazijn_count = content.count('Magazijn')
            numbered_lines = len([l for l in lines if re.match(r'^\d+', l.strip())])
            
            f.write(f"'Nesting' mentions: {nesting_count}\n")
            f.write(f"'Aantal onderdelen' mentions: {aantal_count}\n")
            f.write(f"'Controle' mentions: {controle_count}\n")
            f.write(f"'Magazijn' mentions: {magazijn_count}\n")
            f.write(f"Lines starting with numbers: {numbered_lines}\n")
            
            # Show sample of extracted text
            f.write("\nFirst 10 non-empty lines:\n")
            for i, line in enumerate(lines[:10]):
                f.write(f"{i+1:2d}: {line}\n")
            
            # For TSV, show structure
            if 'tsv' in key:
                f.write("\nTSV Structure Analysis:\n")
                tsv_lines = content.split('\n')
                if len(tsv_lines) > 1:
                    header = tsv_lines[0].split('\t')
                    f.write(f"Columns: {len(header)}\n")
                    f.write(f"Header: {header}\n")
                    
                    # Extract text column (usually column 11)
                    text_items = []
                    for line in tsv_lines[1:11]:  # First 10 data rows
                        parts = line.split('\t')
                        if len(parts) > 11 and parts[11].strip():
                            text_items.append(parts[11])
                    
                    f.write(f"\nText extracted from TSV (first 10 items):\n")
                    for i, item in enumerate(text_items):
                        f.write(f"{i+1:2d}: {item}\n")
            
            f.write("\n" + "=" * 50 + "\n\n")
    
    print(f"✅ Detailed analysis saved to: {analysis_file}")

def test_parsing_on_ocr(results: dict):
    """Test our parsing logic on the OCR output"""
    
    print("\n   Testing NESTING extraction...")
    print("   Testing BOERE extraction...")
    print("   Testing ACCURA extraction...")
    
    # Test on the best-looking result (usually PSM6 text)
    best_result = None
    for key, result in results.items():
        if 'PSM6_txt' in key:
            best_result = result
            break
    
    if not best_result:
        best_result = list(results.values())[0]
    
    content = best_result['content']
    lines = [l.strip() for l in content.split('\n') if l.strip()]
    
    # Test NESTING
    nesting_count = extract_nesting_from_lines(lines)
    print(f"   NESTING extracted: {nesting_count}")
    
    # Test BOERE
    boere_count = extract_boere_from_lines(lines)
    print(f"   BOERE extracted: {boere_count}")
    
    # Test ACCURA
    accura_count = extract_accura_from_lines(lines)
    print(f"   ACCURA extracted: {accura_count}")

def extract_nesting_from_lines(lines):
    """Extract NESTING count from OCR lines"""
    counts = []
    
    for i, line in enumerate(lines):
        if 'Aantal onderdelen' in line:
            # Look for number in this line or next few lines
            for j in range(i, min(i+3, len(lines))):
                numbers = re.findall(r'\b(\d+)\b', lines[j])
                if numbers:
                    count = int(numbers[-1])
                    if 5 <= count <= 100:  # Reasonable range
                        counts.append(count)
                        if len(counts) >= 2:
                            return counts[0] + counts[1]
                        break
    
    return counts[0] if counts else 0

def extract_boere_from_lines(lines):
    """Extract BOERE count from OCR lines"""
    # Find section boundaries
    controle_idx = None
    magazijn_idx = None
    
    for i, line in enumerate(lines):
        if 'Controle' in line and not controle_idx:
            controle_idx = i
        elif 'Magazijn' in line and controle_idx:
            magazijn_idx = i
            break
    
    if not controle_idx:
        return 0
    
    if not magazijn_idx:
        magazijn_idx = len(lines)
    
    # Count numbered items
    count = 0
    for i in range(controle_idx, magazijn_idx):
        line = lines[i]
        if re.match(r'^\d+', line):
            # Check if "te bestellen" nearby
            has_te_bestellen = False
            for j in range(i, min(i+3, magazijn_idx)):
                if 'bestellen' in lines[j].lower():
                    has_te_bestellen = True
                    break
            
            if not has_te_bestellen:
                count += 1
    
    return count

def extract_accura_from_lines(lines):
    """Extract ACCURA count from OCR lines"""
    count = 0
    in_nesting = False
    
    for i, line in enumerate(lines):
        if 'Nesting' in line:
            in_nesting = True
        elif 'Controle' in line:
            in_nesting = False
        
        if in_nesting and re.match(r'^\d+', line):
            # Check for edge processing indicators
            has_edges = False
            for j in range(i, min(i+5, len(lines))):
                check_line = lines[j].lower()
                if ('fineer' in check_line or 
                    'finger' in check_line or
                    re.search(r'\d+mm', check_line) or
                    'standaard' in check_line):
                    has_edges = True
                    break
            
            if has_edges:
                count += 1
    
    return count

def quick_debug_hoekdressing():
    """Quick debug on Hoekdressing PDF"""
    
    pdf_path = 'S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF'
    
    if os.path.exists(pdf_path):
        print(f"📄 Debugging: {os.path.basename(pdf_path)}")
        print("Expected: NESTING=52, BOERE=62, ACCURA=44")
        print("-" * 70)
        
        create_visual_ocr_debug(pdf_path, page_num=2)
    else:
        print(f"❌ PDF not found: {pdf_path}")

def quick_debug_tv_wand():
    """Quick debug on TV-wand PDF"""
    
    pdf_path = 'S04479_RAPPORT_Rudi Matterne_0411_MO07202-7203_TV-wand (7-7).PDF'
    
    if os.path.exists(pdf_path):
        print(f"📄 Debugging: {os.path.basename(pdf_path)}")
        print("Expected: NESTING=102, BOERE=144, ACCURA=84")
        print("-" * 70)
        
        create_visual_ocr_debug(pdf_path, page_num=2)
    else:
        print(f"❌ PDF not found: {pdf_path}")

if __name__ == "__main__":
    print("🔍 VISUAL OCR DEBUGGER")
    print("=" * 50)
    print("This tool shows exactly what happens during OCR processing")
    print("and helps debug why table structure might be getting lost.")
    print()
    
    # Debug the smaller Hoekdressing PDF first
    quick_debug_hoekdressing()