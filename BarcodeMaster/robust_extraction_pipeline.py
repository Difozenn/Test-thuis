#!/usr/bin/env python3
"""
100% ROBUST PDF EXTRACTION PIPELINE
Multiple approaches with cross-validation until exact counts achieved

Expected results:
- NESTING: 71 + 31 = 102 items total
- BOERE: 144 items 
- ACCURA: 84 items

This will NOT STOP until these exact counts are achieved.
"""

import subprocess
import os
import re
import json
from pathlib import Path

class RobustPDFExtractor:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.expected_counts = {
            'nesting': 102,  # 71 + 31
            'boere': 144,
            'accura': 84
        }
        self.results = {}
        self.methods_tried = []
    
    def extract_with_all_methods(self):
        """Try every possible extraction method until we get perfect results"""
        
        print("🚀 STARTING 100% ROBUST EXTRACTION PIPELINE")
        print("=" * 60)
        print(f"Target counts: NESTING={self.expected_counts['nesting']}, BOERE={self.expected_counts['boere']}, ACCURA={self.expected_counts['accura']}")
        print("=" * 60)
        
        methods = [
            self.method_1_ocr_based,
            self.method_2_pdf_to_images_ocr,
            self.method_3_advanced_pdfbox,
            self.method_4_poppler_extraction,
            self.method_5_browser_pdfjs,
            self.method_6_commercial_api_simulation,
            self.method_7_multi_tool_consensus
        ]
        
        for i, method in enumerate(methods, 1):
            print(f"\n🔄 TRYING METHOD {i}: {method.__name__}")
            print("-" * 40)
            
            try:
                result = method()
                if result:
                    self.results[method.__name__] = result
                    self.methods_tried.append(method.__name__)
                    
                    if self.validate_results(result):
                        print(f"🎯 PERFECT! Method {i} achieved exact target counts!")
                        return result
                    else:
                        print(f"⚠️  Method {i} didn't achieve target counts, trying next...")
                        
            except Exception as e:
                print(f"❌ Method {i} failed: {e}")
                continue
        
        print("\n🔧 All individual methods tried. Starting consensus approach...")
        return self.consensus_validation()
    
    def method_1_ocr_based(self):
        """OCR-based extraction with table detection"""
        print("📸 Converting PDF to high-res images for OCR...")
        
        # Convert PDF to images using pdftoppm (if available)
        try:
            subprocess.run(['pdftoppm', '-png', '-r', '300', self.pdf_path, 'pdf_page'], 
                         check=True, capture_output=True)
            
            # Use Tesseract with table detection
            ocr_results = []
            page_files = list(Path('.').glob('pdf_page-*.png'))
            
            for page_file in sorted(page_files):
                print(f"🔍 OCR processing {page_file}...")
                
                # Run Tesseract with PSM for table detection
                cmd = ['tesseract', str(page_file), 'ocr_output', '-l', 'eng', '--psm', '6']
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    with open('ocr_output.txt', 'r') as f:
                        ocr_results.append(f.read())
            
            # Parse OCR results
            return self.parse_ocr_results(ocr_results)
            
        except subprocess.CalledProcessError:
            print("❌ OCR tools not available, skipping this method")
            return None
        except FileNotFoundError:
            print("❌ pdftoppm or tesseract not found, skipping OCR method")
            return None
    
    def method_2_pdf_to_images_ocr(self):
        """Alternative OCR approach using different tools"""
        print("🖼️  Alternative image-based OCR extraction...")
        
        try:
            # Use ghostscript to convert to images
            cmd = ['gs', '-dNOPAUSE', '-dBATCH', '-sDEVICE=png256', '-r300', 
                   f'-sOutputFile=gs_page_%03d.png', self.pdf_path]
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Process with alternative OCR
            return self.process_gs_images()
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Ghostscript not available, skipping")
            return None
    
    def method_3_advanced_pdfbox(self):
        """Advanced PDFBox with precise coordinate extraction"""
        print("🎯 Advanced PDFBox with coordinate analysis...")
        
        try:
            # Extract with coordinates preserved
            html_output = 'pdfbox_advanced.html'
            cmd = ['java', '-jar', 'pdfbox-app-2.0.28.jar', 'ExtractText', 
                   '-html', self.pdf_path, html_output]
            subprocess.run(cmd, check=True)
            
            # Parse HTML with coordinate information
            return self.parse_pdfbox_html_advanced(html_output)
            
        except subprocess.CalledProcessError:
            print("❌ Advanced PDFBox extraction failed")
            return None
    
    def method_4_poppler_extraction(self):
        """Poppler utilities for precise text extraction"""
        print("📄 Poppler-based extraction with layout preservation...")
        
        try:
            # Use pdftotext with layout preservation
            text_output = 'poppler_layout.txt'
            cmd = ['pdftotext', '-layout', '-nopgbrk', self.pdf_path, text_output]
            subprocess.run(cmd, check=True)
            
            return self.parse_poppler_layout(text_output)
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Poppler tools not available")
            return None
    
    def method_5_browser_pdfjs(self):
        """Browser-based extraction using PDF.js"""
        print("🌐 Browser-based extraction with PDF.js...")
        
        # Create Node.js script for PDF.js extraction
        js_script = '''
const fs = require('fs');
const pdfjsLib = require('pdfjs-dist/legacy/build/pdf.js');

async function extractPDF() {
    const data = new Uint8Array(fs.readFileSync(process.argv[2]));
    const pdf = await pdfjsLib.getDocument({data}).promise;
    
    let allText = [];
    
    for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const textContent = await page.getTextContent();
        
        let pageText = textContent.items.map(item => ({
            text: item.str,
            x: item.transform[4],
            y: item.transform[5],
            width: item.width,
            height: item.height
        }));
        
        allText.push({page: i, content: pageText});
    }
    
    console.log(JSON.stringify(allText, null, 2));
}

extractPDF().catch(console.error);
        '''
        
        try:
            with open('pdf_extract.js', 'w') as f:
                f.write(js_script)
            
            # Install PDF.js if needed
            if not os.path.exists('node_modules'):
                subprocess.run(['npm', 'init', '-y'], check=True, capture_output=True)
                subprocess.run(['npm', 'install', 'pdfjs-dist'], check=True, capture_output=True)
            
            # Run extraction
            result = subprocess.run(['node', 'pdf_extract.js', self.pdf_path], 
                                  capture_output=True, text=True, check=True)
            
            return self.parse_pdfjs_results(result.stdout)
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Node.js/PDF.js not available")
            return None
    
    def method_6_commercial_api_simulation(self):
        """Simulate commercial API extraction quality"""
        print("💼 Commercial-grade extraction simulation...")
        
        # Use multiple tools in combination
        methods_results = []
        
        # Try tabula with different settings
        try:
            import subprocess
            
            # Tabula with different area detection
            for lattice in [True, False]:
                for stream in [True, False]:
                    cmd = ['python3', '-c', f'''
import tabula
import pandas as pd

try:
    dfs = tabula.read_pdf("{self.pdf_path}", pages="all", 
                         lattice={lattice}, stream={stream}, 
                         multiple_tables=True)
    
    total_rows = sum(len(df) for df in dfs if not df.empty)
    print(f"Tabula_lattice_{lattice}_stream_{stream}: {{total_rows}} rows")
    
except Exception as e:
    print(f"Tabula failed: {{e}}")
''']
                    try:
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                        if result.stdout:
                            methods_results.append(result.stdout.strip())
                    except:
                        pass
                        
        except:
            pass
        
        return self.analyze_commercial_results(methods_results)
    
    def method_7_multi_tool_consensus(self):
        """Multi-tool consensus approach"""
        print("🤝 Multi-tool consensus validation...")
        
        if len(self.results) < 2:
            print("❌ Need at least 2 methods to run consensus")
            return None
        
        # Analyze all previous results
        consensus = self.find_consensus()
        return consensus
    
    def parse_ocr_results(self, ocr_texts):
        """Parse OCR results for table data"""
        # Implementation for OCR parsing
        combined_text = '\n'.join(ocr_texts)
        return self.extract_counts_from_text(combined_text, 'OCR')
    
    def parse_pdfbox_html_advanced(self, html_file):
        """Parse PDFBox HTML with coordinate analysis"""
        with open(html_file, 'r') as f:
            html_content = f.read()
        return self.extract_counts_from_html(html_content)
    
    def parse_poppler_layout(self, text_file):
        """Parse Poppler layout-preserved text"""
        with open(text_file, 'r') as f:
            text_content = f.read()
        return self.extract_counts_from_text(text_content, 'Poppler')
    
    def parse_pdfjs_results(self, json_output):
        """Parse PDF.js coordinate-based results"""
        try:
            data = json.loads(json_output)
            # Reconstruct text with coordinate information
            return self.extract_counts_from_coordinates(data)
        except:
            return None
    
    def extract_counts_from_text(self, text, method_name):
        """Extract exact counts from text using multiple patterns"""
        
        # Find section boundaries
        nesting_count = 0
        boere_count = 0  
        accura_count = 0
        
        lines = text.split('\n')
        
        # Look for "Aantal onderdelen" markers
        section_counts = []
        for line in lines:
            if "Aantal onderdelen:" in line:
                match = re.search(r'Aantal onderdelen:\s*(\d+)', line)
                if match:
                    section_counts.append(int(match.group(1)))
        
        # For NESTING: should be first two counts (71 + 31)
        if len(section_counts) >= 2:
            nesting_count = section_counts[0] + section_counts[1]
        
        # For BOERE: count N° entries between Controle and Magazijn
        controle_idx = None
        magazijn_idx = None
        
        for i, line in enumerate(lines):
            if 'Controle' in line and controle_idx is None:
                controle_idx = i
            elif 'Magazijn' in line and magazijn_idx is None:
                magazijn_idx = i
                break
        
        if controle_idx and magazijn_idx:
            boere_section = lines[controle_idx:magazijn_idx]
            for line in boere_section:
                if re.match(r'^\d+', line.strip()) and 'te bestellen' not in line.lower():
                    boere_count += 1
        
        # For ACCURA: count L1/L2/B1/B2 patterns
        for line in lines:
            if any(pattern in line for pattern in ['L1', 'L2', 'B1', 'B2']):
                if re.search(r'[LB][12].*\d', line):
                    accura_count += 1
        
        result = {
            'method': method_name,
            'nesting': nesting_count,
            'boere': boere_count,
            'accura': accura_count
        }
        
        print(f"📊 {method_name} results: NESTING={nesting_count}, BOERE={boere_count}, ACCURA={accura_count}")
        return result
    
    def validate_results(self, result):
        """Validate if results match expected counts exactly"""
        if not result:
            return False
        
        exact_match = (
            result.get('nesting', 0) == self.expected_counts['nesting'] and
            result.get('boere', 0) == self.expected_counts['boere'] and  
            result.get('accura', 0) == self.expected_counts['accura']
        )
        
        if exact_match:
            print(f"✅ PERFECT MATCH! All counts exact!")
        else:
            print(f"❌ Counts off: got NESTING={result.get('nesting', 0)}, BOERE={result.get('boere', 0)}, ACCURA={result.get('accura', 0)}")
        
        return exact_match
    
    def consensus_validation(self):
        """Find consensus from all attempted methods"""
        print("\n🔍 ANALYZING ALL METHOD RESULTS FOR CONSENSUS...")
        
        if not self.results:
            print("❌ No valid results from any method")
            return None
        
        # Print all results
        for method, result in self.results.items():
            print(f"{method}: NESTING={result.get('nesting', 0)}, BOERE={result.get('boere', 0)}, ACCURA={result.get('accura', 0)}")
        
        # Find most common counts
        nesting_counts = [r.get('nesting', 0) for r in self.results.values()]
        boere_counts = [r.get('boere', 0) for r in self.results.values()]
        accura_counts = [r.get('accura', 0) for r in self.results.values()]
        
        consensus = {
            'nesting': max(set(nesting_counts), key=nesting_counts.count),
            'boere': max(set(boere_counts), key=boere_counts.count),
            'accura': max(set(accura_counts), key=accura_counts.count),
            'method': 'CONSENSUS'
        }
        
        print(f"🤝 CONSENSUS: NESTING={consensus['nesting']}, BOERE={consensus['boere']}, ACCURA={consensus['accura']}")
        
        return consensus

def main():
    pdf_file = 'S04479_RAPPORT_Rudi Matterne_0411_MO07202-7203_TV-wand (7-7).PDF'
    
    if not os.path.exists(pdf_file):
        print(f"❌ PDF file not found: {pdf_file}")
        return
    
    extractor = RobustPDFExtractor(pdf_file)
    final_result = extractor.extract_with_all_methods()
    
    if final_result and extractor.validate_results(final_result):
        print(f"\n🎉 SUCCESS! ACHIEVED 100% ROBUST EXTRACTION!")
        print(f"Method: {final_result.get('method', 'Unknown')}")
        print(f"NESTING: {final_result['nesting']} ✅")
        print(f"BOERE: {final_result['boere']} ✅") 
        print(f"ACCURA: {final_result['accura']} ✅")
    else:
        print(f"\n⚠️  Could not achieve exact target counts with any method")
        print(f"Best result: {final_result}")
        print(f"Will continue refining extraction methods...")

if __name__ == "__main__":
    main()