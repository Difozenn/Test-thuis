#!/usr/bin/env python3
"""
TRULY SIMPLE SOLUTION
BOERE: Every row with a number in N° column between Controle and Magazijn (excluding "te bestellen")
It's that simple!
"""

import re
import os
import subprocess

class TrulySimpleExtractor:
    """Simple, correct implementation"""
    
    def __init__(self):
        self.pdfbox_jar = 'pdfbox-app-2.0.28.jar'
    
    def extract_pdf_data(self, pdf_path: str) -> dict:
        """Extract with simple, correct logic"""
        
        print(f"🚀 Extracting from: {os.path.basename(pdf_path)}")
        
        # Extract text
        text_file = pdf_path.replace('.PDF', '_simple.txt').replace('.pdf', '_simple.txt')
        
        if not os.path.exists(text_file):
            cmd = ['java', '-jar', self.pdfbox_jar, 'ExtractText', pdf_path, text_file]
            subprocess.run(cmd, capture_output=True, text=True)
        
        with open(text_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        results = {
            'nesting': self._get_nesting_count(lines),
            'boere': self._get_boere_count_simple(lines),
            'accura': self._get_accura_count(lines),
            'method': 'Simple and Correct'
        }
        
        print(f"✅ NESTING={results['nesting']}, BOERE={results['boere']}, ACCURA={results['accura']}")
        
        return results
    
    def _get_nesting_count(self, lines):
        """Sum first two 'Aantal onderdelen' markers"""
        counts = []
        for line in lines:
            if "Aantal onderdelen:" in line:
                match = re.search(r'Aantal onderdelen:\s*(\d+)', line)
                if match:
                    counts.append(int(match.group(1)))
                    if len(counts) >= 2:
                        return counts[0] + counts[1]
        return counts[0] if counts else 0
    
    def _get_boere_count_simple(self, lines):
        """
        BOERE: It's simple!
        Count every row with a number in N° column between Controle and Magazijn
        Exclude rows with "te bestellen"
        """
        
        # Find Controle and Magazijn boundaries
        controle_idx = None
        magazijn_idx = None
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            if 'Controle' in line_clean and controle_idx is None:
                controle_idx = i
            elif 'Magazijn' in line_clean and controle_idx is not None and magazijn_idx is None:
                magazijn_idx = i
                break
        
        if not controle_idx:
            print("❌ No Controle section found")
            return 0
        
        if not magazijn_idx:
            # Find any Magazijn after Controle
            for i in range(controle_idx + 1, len(lines)):
                if 'Magazijn' in lines[i]:
                    magazijn_idx = i
                    break
        
        if not magazijn_idx:
            magazijn_idx = len(lines)
        
        print(f"📍 BOERE section: lines {controle_idx} to {magazijn_idx}")
        
        # Count all numbered rows (excluding "te bestellen")
        boere_count = 0
        te_bestellen_count = 0
        
        for i in range(controle_idx, magazijn_idx):
            line = lines[i].strip()
            
            # If line starts with a number (N° column has a number)
            if re.match(r'^\d+', line):
                # Check if it contains "te bestellen"
                if 'te bestellen' in line.lower():
                    te_bestellen_count += 1
                else:
                    boere_count += 1
        
        print(f"   Found {boere_count} BOERE items (excluded {te_bestellen_count} 'te bestellen')")
        
        return boere_count
    
    def _get_accura_count(self, lines):
        """Count NESTING items with edge processing (multi-line items)"""
        
        accura_count = 0
        in_nesting = False
        current_item_line = None
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            
            # Track sections
            if 'Nesting' in line:
                in_nesting = True
            elif 'Controle' in line:
                in_nesting = False
            
            if in_nesting:
                # New numbered item
                if re.match(r'^\d+\s+\w+', line_clean) and len(line_clean.split()) >= 4:
                    # Check if previous item was multi-line
                    if current_item_line is not None:
                        lines_used = i - current_item_line
                        if lines_used > 3:  # Multi-line = has edges
                            accura_count += 1
                    current_item_line = i
                
                # End of section or empty line
                elif (line_clean == '' or 'Aantal onderdelen' in line) and current_item_line:
                    lines_used = i - current_item_line
                    if lines_used > 3:
                        accura_count += 1
                    current_item_line = None
        
        return accura_count

def test_simple_solution():
    """Test the simple solution"""
    
    print("🧪 TESTING SIMPLE SOLUTION")
    print("=" * 70)
    print("BOERE = All numbered rows between Controle and Magazijn (except 'te bestellen')")
    print("=" * 70)
    
    test_cases = [
        {
            'pdf': 'S04479_RAPPORT_Rudi Matterne_0411_MO07202-7203_TV-wand (7-7).PDF',
            'name': 'TV-wand',
            'expected': {'nesting': 102, 'boere': 144, 'accura': 84}
        },
        {
            'pdf': 'S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF',
            'name': 'Hoekdressing',
            'expected': {'nesting': 52, 'boere': 62, 'accura': 44}
        }
    ]
    
    extractor = TrulySimpleExtractor()
    
    for test in test_cases:
        if os.path.exists(test['pdf']):
            print(f"\n📄 {test['name']}")
            print(f"Expected: N={test['expected']['nesting']}, B={test['expected']['boere']}, A={test['expected']['accura']}")
            print("-" * 60)
            
            result = extractor.extract_pdf_data(test['pdf'])
            
            print(f"\n📊 Results:")
            print(f"NESTING: {result['nesting']} (expected {test['expected']['nesting']}) "
                  f"{'✅' if result['nesting'] == test['expected']['nesting'] else '❌'}")
            print(f"BOERE: {result['boere']} (expected {test['expected']['boere']}) "
                  f"{'✅' if result['boere'] == test['expected']['boere'] else '❌'}")
            print(f"ACCURA: {result['accura']} (expected {test['expected']['accura']}) "
                  f"{'✅' if result['accura'] == test['expected']['accura'] else '❌'}")
            
            # If BOERE is still wrong, let's debug
            if result['boere'] != test['expected']['boere']:
                print(f"\n🔍 BOERE Debug: Got {result['boere']}, expected {test['expected']['boere']}")
                print(f"   Difference: {result['boere'] - test['expected']['boere']}")

if __name__ == "__main__":
    test_simple_solution()