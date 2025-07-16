#!/usr/bin/env python3
"""
TRULY DYNAMIC EXTRACTOR - Actually calculates real counts for each PDF
No hardcoded fallbacks!
"""

import subprocess
import re
import os

class TrulyDynamicExtractor:
    """Actually dynamic PDF extractor - no hardcoded values"""
    
    def __init__(self):
        self.pdfbox_jar = 'pdfbox-app-2.0.28.jar'
        
    def extract_pdf_data(self, pdf_path: str) -> dict:
        """Extract actual counts from any PDF"""
        
        print(f"🚀 Extracting actual counts from: {pdf_path}")
        
        # Step 1: Extract text with PDFBox
        text_file = self._extract_text_with_pdfbox(pdf_path)
        if not text_file:
            raise Exception("PDFBox text extraction failed")
        
        # Step 2: Parse with truly dynamic methods
        with open(text_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Find all section boundaries dynamically
        section_info = self._analyze_pdf_structure(lines)
        
        results = {
            'nesting': self._get_dynamic_nesting_count(lines, section_info),
            'boere': self._get_dynamic_boere_count(lines, section_info), 
            'accura': self._get_dynamic_accura_count(lines, section_info),
            'method': 'Truly Dynamic Extraction',
            'pdf_file': os.path.basename(pdf_path)
        }
        
        print(f"✅ Dynamic extraction complete: NESTING={results['nesting']}, BOERE={results['boere']}, ACCURA={results['accura']}")
        
        return results
    
    def _extract_text_with_pdfbox(self, pdf_path: str) -> str:
        """Extract text using Java PDFBox"""
        
        text_output = pdf_path.replace('.PDF', '_dynamic.txt').replace('.pdf', '_dynamic.txt')
        
        print(f"🔄 Extracting text with PDFBox...")
        cmd = ['java', '-jar', self.pdfbox_jar, 'ExtractText', pdf_path, text_output]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ PDFBox failed: {result.stderr}")
            return None
        
        print(f"✅ Text extracted: {text_output}")
        return text_output
    
    def _analyze_pdf_structure(self, lines):
        """Dynamically analyze PDF structure"""
        
        structure = {
            'aantal_markers': [],
            'controle_line': None,
            'magazijn_lines': [],
            'nesting_start': None,
            'section_headers': []
        }
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            
            # Find all "Aantal onderdelen" markers
            if "Aantal onderdelen:" in line:
                match = re.search(r'Aantal onderdelen:\s*(\d+)', line)
                if match:
                    count = int(match.group(1))
                    structure['aantal_markers'].append((i, count))
            
            # Find section headers
            if 'Nesting' in line and not structure['nesting_start']:
                structure['nesting_start'] = i
            elif 'Controle' in line_clean and not structure['controle_line']:
                structure['controle_line'] = i
            elif 'Magazijn' in line_clean:
                structure['magazijn_lines'].append(i)
        
        print(f"📊 PDF Structure Analysis:")
        print(f"   - Found {len(structure['aantal_markers'])} 'Aantal onderdelen' markers")
        print(f"   - Controle at line: {structure['controle_line']}")
        print(f"   - Magazijn at lines: {structure['magazijn_lines']}")
        
        return structure
    
    def _get_dynamic_nesting_count(self, lines, structure):
        """Dynamically calculate NESTING count"""
        
        # NESTING is typically first two "Aantal onderdelen" sections
        if len(structure['aantal_markers']) >= 2:
            count1 = structure['aantal_markers'][0][1]
            count2 = structure['aantal_markers'][1][1]
            total = count1 + count2
            print(f"   NESTING: {count1} + {count2} = {total}")
            return total
        elif len(structure['aantal_markers']) >= 1:
            # Only one section
            return structure['aantal_markers'][0][1]
        
        # Fallback: count items manually
        return self._count_nesting_items(lines, structure)
    
    def _get_dynamic_boere_count(self, lines, structure):
        """Dynamically calculate BOERE count"""
        
        if not structure['controle_line']:
            print("   ⚠️  No Controle section found")
            return 0
        
        # Find the correct Magazijn boundary after Controle
        start = structure['controle_line']
        end = len(lines)
        
        for mag_line in structure['magazijn_lines']:
            if mag_line > start:
                end = mag_line
                break
        
        print(f"   BOERE section: lines {start} to {end}")
        
        # Count items between Controle and Magazijn
        count = 0
        te_bestellen_count = 0
        
        for i in range(start, end):
            line = lines[i].strip()
            # Count numbered items
            if re.match(r'^\d+\s+', line):
                if 'te bestellen' in line.lower():
                    te_bestellen_count += 1
                else:
                    count += 1
        
        print(f"   BOERE: {count} items (excluded {te_bestellen_count} 'Te bestellen')")
        return count
    
    def _get_dynamic_accura_count(self, lines, structure):
        """Dynamically calculate ACCURA count"""
        
        # Method 1: Count all L1/L2/B1/B2 patterns
        pattern_count = 0
        for line in lines:
            if any(p in line for p in ['L1', 'L2', 'B1', 'B2']):
                if re.search(r'[LB][12].*\d', line):
                    pattern_count += 1
        
        # Method 2: Count items in sections with L1/L2/B1/B2 headers
        table_count = self._count_accura_table_items(lines)
        
        # Method 3: Sum relevant "Aantal onderdelen" sections
        section_sum = self._sum_accura_sections(lines, structure)
        
        print(f"   ACCURA methods: patterns={pattern_count}, tables={table_count}, sections={section_sum}")
        
        # Return the most reasonable count
        if table_count > 0:
            return table_count
        elif section_sum > 0:
            return section_sum
        else:
            return pattern_count
    
    def _count_nesting_items(self, lines, structure):
        """Manually count NESTING items"""
        start = structure['nesting_start'] if structure['nesting_start'] else 0
        end = structure['controle_line'] if structure['controle_line'] else len(lines)
        
        count = 0
        for i in range(start, end):
            line = lines[i].strip()
            if re.match(r'^\d+\s+', line) and len(line.split()) >= 4:
                count += 1
        
        return count
    
    def _count_accura_table_items(self, lines):
        """Count ACCURA items in table format"""
        count = 0
        in_table = False
        
        for line in lines:
            # Check for L1/L2/B1/B2 table header
            if 'L1' in line and 'L2' in line and 'B1' in line and 'B2' in line:
                in_table = True
                continue
            
            if in_table:
                # Count numbered rows in the table
                if re.match(r'^\d+\s+', line.strip()):
                    count += 1
                elif line.strip() == '' or 'Aantal onderdelen' in line:
                    in_table = False
        
        return count
    
    def _sum_accura_sections(self, lines, structure):
        """Sum counts from ACCURA-related sections"""
        total = 0
        
        for line_num, count in structure['aantal_markers']:
            # Check context around this marker
            context_start = max(0, line_num - 5)
            context_end = min(len(lines), line_num + 5)
            context = ' '.join(lines[context_start:context_end]).lower()
            
            # If context suggests ACCURA processing
            if any(keyword in context for keyword in ['l1', 'l2', 'b1', 'b2', 'accura']):
                total += count
        
        return total

def test_both_pdfs():
    """Test the truly dynamic solution on both PDFs"""
    
    print("🧪 TESTING TRULY DYNAMIC SOLUTION ON BOTH PDFs")
    print("=" * 70)
    
    pdfs = [
        'S04479_RAPPORT_Rudi Matterne_0411_MO07202-7203_TV-wand (7-7).PDF',
        'S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF'
    ]
    
    extractor = TrulyDynamicExtractor()
    results = {}
    
    for pdf in pdfs:
        if os.path.exists(pdf):
            print(f"\n📄 Testing: {pdf}")
            print("-" * 60)
            
            result = extractor.extract_pdf_data(pdf)
            results[pdf] = result
            
            print(f"\n📊 Results for {os.path.basename(pdf)}:")
            print(f"   NESTING: {result['nesting']}")
            print(f"   BOERE: {result['boere']}")
            print(f"   ACCURA: {result['accura']}")
    
    # Compare results
    if len(results) == 2:
        print(f"\n📊 COMPARISON:")
        print("=" * 60)
        
        pdf1, pdf2 = list(results.keys())
        r1, r2 = results[pdf1], results[pdf2]
        
        print(f"PDF 1: {os.path.basename(pdf1)}")
        print(f"   NESTING: {r1['nesting']}")
        print(f"   BOERE: {r1['boere']}")
        print(f"   ACCURA: {r1['accura']}")
        
        print(f"\nPDF 2: {os.path.basename(pdf2)}")
        print(f"   NESTING: {r2['nesting']}")
        print(f"   BOERE: {r2['boere']}")
        print(f"   ACCURA: {r2['accura']}")
        
        print(f"\n✅ TRULY DYNAMIC:")
        print(f"   NESTING different: {r1['nesting']} vs {r2['nesting']}")
        print(f"   BOERE calculated: {r1['boere']} vs {r2['boere']}")
        print(f"   ACCURA calculated: {r1['accura']} vs {r2['accura']}")

if __name__ == "__main__":
    test_both_pdfs()