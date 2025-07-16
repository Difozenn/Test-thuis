#!/usr/bin/env python3
"""
ALTERNATIVE PDF CONVERTERS
Try different PDF to Excel conversion methods
"""

import subprocess
import os
import requests
import time

def convert_with_pdf2csv_direct(pdf_path: str) -> str:
    """Convert PDF to CSV using pdf2csv command line tool"""
    
    print("🔄 Converting with pdf2csv...")
    
    csv_file = pdf_path.replace('.PDF', '_direct.csv').replace('.pdf', '_direct.csv')
    
    try:
        # Try pdf2csv if available
        cmd = ['pdf2csv', pdf_path, csv_file]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(csv_file):
            print(f"✅ pdf2csv conversion successful: {csv_file}")
            return csv_file
        else:
            print(f"   pdf2csv not available or failed")
    except FileNotFoundError:
        print("   pdf2csv not installed")
    
    return None

def convert_with_pdftables(pdf_path: str) -> str:
    """Convert using pdftables.com API (if API key available)"""
    
    print("🔄 Converting with pdftables.com...")
    
    # This would require an API key - placeholder for now
    print("   pdftables.com requires API key (not implemented)")
    return None

def convert_with_adobe_acrobat_dc(pdf_path: str) -> str:
    """Convert using Adobe Acrobat DC command line (if available)"""
    
    print("🔄 Converting with Adobe Acrobat DC...")
    
    xlsx_file = pdf_path.replace('.PDF', '_acrobat.xlsx').replace('.pdf', '_acrobat.xlsx')
    
    try:
        # Adobe Acrobat command line syntax varies by platform
        cmd = ['acrobat', '/n', '/t', 'ExportPDF', 'xlsx', pdf_path, xlsx_file]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0 and os.path.exists(xlsx_file):
            print(f"✅ Adobe Acrobat conversion successful: {xlsx_file}")
            return xlsx_file
        else:
            print("   Adobe Acrobat not available or failed")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("   Adobe Acrobat not installed or timeout")
    
    return None

def convert_with_java_pdfbox_export(pdf_path: str) -> str:
    """Convert using Java PDFBox to export to structured format"""
    
    print("🔄 Converting with Java PDFBox export...")
    
    csv_file = pdf_path.replace('.PDF', '_pdfbox_export.csv').replace('.pdf', '_pdfbox_export.csv')
    
    try:
        # Use PDFBox to export text in a more structured way
        cmd = [
            'java', '-jar', 'pdfbox-app-2.0.28.jar', 
            'ExtractText', 
            '-console',
            '-encoding', 'UTF-8',
            pdf_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Parse the output into CSV format
            lines = result.stdout.split('\n')
            
            import csv
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['page', 'line_num', 'content'])
                
                current_page = 1
                for i, line in enumerate(lines):
                    line = line.strip()
                    if line:
                        # Detect page breaks
                        if 'Page' in line and 'of' in line:
                            try:
                                import re
                                current_page = int(re.search(r'Page (\d+)', line).group(1))
                            except:
                                pass
                        else:
                            writer.writerow([current_page, i, line])
            
            print(f"✅ PDFBox export conversion successful: {csv_file}")
            return csv_file
        
    except Exception as e:
        print(f"   PDFBox export failed: {e}")
    
    return None

def convert_with_ghostscript_text(pdf_path: str) -> str:
    """Convert using Ghostscript text extraction"""
    
    print("🔄 Converting with Ghostscript...")
    
    txt_file = pdf_path.replace('.PDF', '_ghostscript.txt').replace('.pdf', '_ghostscript.txt')
    csv_file = pdf_path.replace('.PDF', '_ghostscript.csv').replace('.pdf', '_ghostscript.csv')
    
    try:
        # Use Ghostscript to extract text
        cmd = [
            'gs', 
            '-dNOPAUSE', '-dBATCH', '-dSAFER',
            '-sDEVICE=txtwrite',
            f'-sOutputFile={txt_file}',
            pdf_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(txt_file):
            # Convert text to CSV
            import csv
            import re
            
            with open(txt_file, 'r', encoding='utf-8') as f:
                text = f.read()
            
            lines = text.split('\n')
            
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['line_num', 'content', 'is_table_row', 'has_numbers'])
                
                for i, line in enumerate(lines):
                    line = line.strip()
                    if line:
                        is_table_row = bool(re.match(r'^\d+\s+\w+', line))
                        has_numbers = bool(re.search(r'\d+', line))
                        writer.writerow([i, line, is_table_row, has_numbers])
            
            # Clean up
            os.remove(txt_file)
            
            print(f"✅ Ghostscript conversion successful: {csv_file}")
            return csv_file
        
    except Exception as e:
        print(f"   Ghostscript failed: {e}")
    
    return None

def convert_with_popplerutils_detailed(pdf_path: str) -> str:
    """Convert using poppler-utils with detailed text extraction"""
    
    print("🔄 Converting with poppler-utils detailed...")
    
    csv_file = pdf_path.replace('.PDF', '_poppler.csv').replace('.pdf', '_poppler.csv')
    
    try:
        # Use pdftotext with layout preservation
        cmd = ['pdftotext', '-layout', '-nopgbrk', pdf_path, '-']
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            import csv
            import re
            
            lines = result.stdout.split('\n')
            
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['line_num', 'content', 'indent_level', 'is_numbered', 'has_section_header'])
                
                for i, line in enumerate(lines):
                    if line.strip():
                        # Analyze line characteristics
                        indent_level = len(line) - len(line.lstrip())
                        is_numbered = bool(re.match(r'^\s*\d+\s+\w+', line))
                        has_section_header = any(header in line for header in ['Nesting', 'Opdeelzaag', 'Controle', 'Massief', 'Magazijn'])
                        
                        writer.writerow([i, line.strip(), indent_level, is_numbered, has_section_header])
            
            print(f"✅ Poppler-utils conversion successful: {csv_file}")
            return csv_file
        
    except Exception as e:
        print(f"   Poppler-utils failed: {e}")
    
    return None

def test_alternative_converters():
    """Test all alternative conversion methods"""
    
    pdf_path = 'S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF'
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print("🎯 TESTING ALTERNATIVE PDF CONVERTERS")
    print("=" * 70)
    
    methods = [
        ('PDF2CSV Direct', convert_with_pdf2csv_direct),
        ('Java PDFBox Export', convert_with_java_pdfbox_export),
        ('Ghostscript Text', convert_with_ghostscript_text),
        ('Poppler-utils Detailed', convert_with_popplerutils_detailed),
        ('Adobe Acrobat DC', convert_with_adobe_acrobat_dc),
    ]
    
    successful_conversions = []
    
    for method_name, method_func in methods:
        print(f"\n📊 Testing {method_name}...")
        
        try:
            result_file = method_func(pdf_path)
            
            if result_file and os.path.exists(result_file):
                # Check file size and content
                file_size = os.path.getsize(result_file)
                print(f"   ✅ Success: {result_file} ({file_size} bytes)")
                
                # Quick content check
                with open(result_file, 'r', encoding='utf-8') as f:
                    content = f.read(1000)  # First 1000 chars
                    has_nesting = 'nesting' in content.lower()
                    has_aantal = 'aantal' in content.lower()
                    has_numbers = any(c.isdigit() for c in content)
                    
                    print(f"   Content check: Nesting={has_nesting}, Aantal={has_aantal}, Numbers={has_numbers}")
                
                successful_conversions.append({
                    'method': method_name,
                    'file': result_file,
                    'size': file_size,
                    'has_nesting': has_nesting,
                    'has_aantal': has_aantal,
                    'has_numbers': has_numbers
                })
            else:
                print(f"   ❌ Failed or no output file")
        
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n🏆 SUMMARY:")
    if successful_conversions:
        print(f"Successful conversions: {len(successful_conversions)}")
        for conv in successful_conversions:
            print(f"  - {conv['method']}: {conv['file']} ({conv['size']} bytes)")
        
        # Recommend best option
        best = max(successful_conversions, key=lambda x: x['size'] + (10000 if x['has_aantal'] else 0))
        print(f"\n🎯 RECOMMENDED: {best['method']} - {best['file']}")
    else:
        print("❌ No successful conversions")

if __name__ == "__main__":
    test_alternative_converters()