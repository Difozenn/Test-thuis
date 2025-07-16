#!/usr/bin/env python3
"""
Raw Text to Structured Data - Extract clean structured data from PDF text
Skip Excel conversion entirely, go directly from PDF text to structured data
"""

import pdfplumber
import re
import csv
import json
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

@dataclass
class StructuredItem:
    """Clean structured item for all users"""
    page_number: int
    item_number: str
    onderdeel: str
    materiaal: str
    lengte: Optional[str] = None
    breedte: Optional[str] = None
    dikte: Optional[str] = None
    l1: Optional[str] = None
    l2: Optional[str] = None
    b1: Optional[str] = None
    b2: Optional[str] = None
    pro_methode: Optional[str] = None
    opmerkingen: Optional[str] = None
    source_line: str = ""
    is_te_bestellen: bool = False

class RawTextToStructured:
    def __init__(self):
        pass
    
    def extract_all_structured_data(self, pdf_path: str) -> Dict[str, any]:
        """Extract all data as structured items, skip Excel completely"""
        
        print("🔄 Extracting structured data directly from PDF text...")
        
        all_items = []
        
        with pdfplumber.open(pdf_path) as pdf:
            # Process relevant pages
            target_pages = list(range(2, 8)) + list(range(11, 26))
            
            for page_num in target_pages:
                if page_num <= len(pdf.pages):
                    page = pdf.pages[page_num-1]
                    page_items = self._extract_page_items_from_text(page, page_num)
                    all_items.extend(page_items)
                    
                    print(f"  Page {page_num}: {len(page_items)} items")
        
        # Save raw structured data
        self._save_structured_data(all_items)
        
        # Generate results for each user type
        results = {
            'nesting': self._filter_for_nesting(all_items),
            'boere': self._filter_for_boere(all_items),
            'accura': self._filter_for_accura(all_items),
            'all_items': len(all_items)
        }
        
        print(f"📊 Total structured items: {len(all_items)}")
        return results
    
    def _extract_page_items_from_text(self, page, page_num: int) -> List[StructuredItem]:
        """Extract structured items from page text"""
        
        items = []
        text = page.extract_text() or ""
        lines = text.split('\n')
        
        # Method 1: Extract from tables if available
        tables = page.extract_tables()
        if tables:
            for table in tables:
                table_items = self._extract_from_table_structured(table, page_num)
                items.extend(table_items)
        
        # Method 2: Extract from raw text lines
        text_items = self._extract_from_text_lines(lines, page_num)
        
        # Combine and deduplicate
        combined_items = self._merge_and_deduplicate(items, text_items)
        
        return combined_items
    
    def _extract_from_table_structured(self, table: List[List], page_num: int) -> List[StructuredItem]:
        """Extract structured items from table"""
        
        items = []
        
        if not table or len(table) < 1:
            return items
        
        # Detect header row
        header_row = None
        data_start = 0
        
        for i, row in enumerate(table):
            if row and self._is_header_row(row):
                header_row = row
                data_start = i + 1
                break
        
        # Map columns
        column_map = {}
        if header_row:
            column_map = self._map_columns_from_header(header_row)
        else:
            # Use positional mapping
            column_map = self._get_positional_column_map(len(table[0]) if table else 0)
        
        # Extract data rows
        for row_idx in range(data_start, len(table)):
            row = table[row_idx]
            if not row:
                continue
            
            item = self._create_structured_item_from_row(row, column_map, page_num, row_idx)
            if item:
                items.append(item)
        
        return items
    
    def _extract_from_text_lines(self, lines: List[str], page_num: int) -> List[StructuredItem]:
        """Extract structured items from text lines"""
        
        items = []
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Look for item lines (start with number)
            if re.match(r'^\d+\s', line):
                item = self._parse_text_line_to_item(line, page_num, line_num)
                if item:
                    items.append(item)
        
        return items
    
    def _parse_text_line_to_item(self, line: str, page_num: int, line_num: int) -> Optional[StructuredItem]:
        """Parse a single text line into structured item"""
        
        # Basic pattern: NUMBER COMPONENT MATERIAL [dimensions] [method]
        parts = line.split()
        if len(parts) < 2:
            return None
        
        item_number = parts[0]
        onderdeel = parts[1] if len(parts) > 1 else ""
        
        # Extract material (usually 3rd or 4th element)
        materiaal = ""
        for i in range(2, min(5, len(parts))):
            if len(parts[i]) > 2 and not parts[i].replace('.', '').isdigit():
                materiaal = parts[i]
                break
        
        # Check for Te bestellen
        is_te_bestellen = 'Te bestellen' in line or 'TE BESTELLEN' in line.upper()
        
        # Extract production method
        pro_methode = ""
        if 'Standaard' in line:
            pro_methode = 'Standaard'
        elif 'Reichenbach' in line:
            pro_methode = 'Reichenbach'
        elif 'Gannomat' in line:
            pro_methode = 'Gannomat'
        elif is_te_bestellen:
            pro_methode = 'Te bestellen'
        
        # Extract dimensions (look for number patterns)
        dimensions = re.findall(r'\d+(?:\.\d+)?', line)
        lengte = dimensions[0] if len(dimensions) > 0 else None
        breedte = dimensions[1] if len(dimensions) > 1 else None
        dikte = dimensions[2] if len(dimensions) > 2 else None
        
        return StructuredItem(
            page_number=page_num,
            item_number=item_number,
            onderdeel=onderdeel,
            materiaal=materiaal,
            lengte=lengte,
            breedte=breedte,
            dikte=dikte,
            pro_methode=pro_methode,
            source_line=line,
            is_te_bestellen=is_te_bestellen
        )
    
    def _is_header_row(self, row: List) -> bool:
        """Check if row is a header"""
        if not row:
            return False
        
        row_text = ' '.join(str(cell or '') for cell in row).upper()
        header_keywords = ['ONDERDEEL', 'MATERIAAL', 'LENGTE', 'BREEDTE', 'DIKTE', 'L1', 'L2', 'B1', 'B2']
        
        return any(keyword in row_text for keyword in header_keywords)
    
    def _map_columns_from_header(self, header: List) -> Dict[str, int]:
        """Map column names from header row"""
        
        column_map = {}
        
        for i, cell in enumerate(header):
            if not cell:
                continue
            
            cell_text = str(cell).upper().strip()
            
            if any(pattern in cell_text for pattern in ['N°', 'NO', 'NUM']):
                column_map['item_number'] = i
            elif 'ONDERDEEL' in cell_text:
                column_map['onderdeel'] = i
            elif 'MATERIAAL' in cell_text:
                column_map['materiaal'] = i
            elif 'LENGTE' in cell_text:
                column_map['lengte'] = i
            elif 'BREEDTE' in cell_text:
                column_map['breedte'] = i
            elif 'DIKTE' in cell_text:
                column_map['dikte'] = i
            elif cell_text == 'L1':
                column_map['l1'] = i
            elif cell_text == 'L2':
                column_map['l2'] = i
            elif cell_text == 'B1':
                column_map['b1'] = i
            elif cell_text == 'B2':
                column_map['b2'] = i
            elif 'PRO.METHODE' in cell_text:
                column_map['pro_methode'] = i
        
        return column_map
    
    def _get_positional_column_map(self, num_cols: int) -> Dict[str, int]:
        """Get positional column mapping when no header"""
        
        if num_cols >= 11:  # Full table with L1/L2/B1/B2
            return {
                'item_number': 0,
                'onderdeel': 1,
                'materiaal': 2,
                'lengte': 3,
                'breedte': 4,
                'dikte': 5,
                'l1': 6,
                'l2': 7,
                'b1': 8,
                'b2': 9,
                'pro_methode': 10
            }
        else:  # Basic table
            return {
                'item_number': 0,
                'onderdeel': 1,
                'materiaal': 2,
                'lengte': 3,
                'breedte': 4,
                'dikte': 5
            }
    
    def _create_structured_item_from_row(self, row: List, column_map: Dict[str, int], 
                                       page_num: int, row_idx: int) -> Optional[StructuredItem]:
        """Create structured item from table row"""
        
        def get_cell_value(field: str) -> Optional[str]:
            col_idx = column_map.get(field)
            if col_idx is not None and col_idx < len(row) and row[col_idx]:
                return str(row[col_idx]).strip() or None
            return None
        
        # Extract all fields
        item_number = get_cell_value('item_number') or str(row_idx)
        onderdeel = get_cell_value('onderdeel') or ""
        materiaal = get_cell_value('materiaal') or ""
        
        # Skip if no meaningful content
        if not onderdeel and not materiaal:
            return None
        
        # Check for Te bestellen
        row_text = ' '.join(str(cell or '') for cell in row)
        is_te_bestellen = 'Te bestellen' in row_text or 'TE BESTELLEN' in row_text.upper()
        
        return StructuredItem(
            page_number=page_num,
            item_number=item_number,
            onderdeel=onderdeel,
            materiaal=materiaal,
            lengte=get_cell_value('lengte'),
            breedte=get_cell_value('breedte'),
            dikte=get_cell_value('dikte'),
            l1=get_cell_value('l1'),
            l2=get_cell_value('l2'),
            b1=get_cell_value('b1'),
            b2=get_cell_value('b2'),
            pro_methode=get_cell_value('pro_methode'),
            source_line=row_text,
            is_te_bestellen=is_te_bestellen
        )
    
    def _merge_and_deduplicate(self, table_items: List[StructuredItem], 
                              text_items: List[StructuredItem]) -> List[StructuredItem]:
        """Merge table and text items, removing duplicates"""
        
        # Use table items as primary, supplement with text items
        seen_signatures = set()
        merged_items = []
        
        # Add table items first
        for item in table_items:
            signature = f"{item.page_number}_{item.onderdeel}_{item.materiaal}"
            if signature not in seen_signatures:
                seen_signatures.add(signature)
                merged_items.append(item)
        
        # Add text items that weren't captured in tables
        for item in text_items:
            signature = f"{item.page_number}_{item.onderdeel}_{item.materiaal}"
            if signature not in seen_signatures:
                seen_signatures.add(signature)
                merged_items.append(item)
        
        return merged_items
    
    def _save_structured_data(self, items: List[StructuredItem]):
        """Save structured data to files"""
        
        # Save as JSON
        json_data = [asdict(item) for item in items]
        with open('structured_data.json', 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        # Save as CSV
        if items:
            with open('structured_data.csv', 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=asdict(items[0]).keys())
                writer.writeheader()
                for item in items:
                    writer.writerow(asdict(item))
        
        print(f"💾 Saved structured data: structured_data.json & structured_data.csv")
    
    def _filter_for_nesting(self, items: List[StructuredItem]) -> Dict[str, int]:
        """Filter for NESTING user"""
        nesting_items = [item for item in items if item.page_number in [2, 3, 4, 5]]
        opdeelzaag_items = [item for item in items if item.page_number in [6, 7]]
        
        return {
            'nesting_count': len(nesting_items),
            'opdeelzaag_count': len(opdeelzaag_items),
            'total_count': len(nesting_items) + len(opdeelzaag_items)
        }
    
    def _filter_for_boere(self, items: List[StructuredItem]) -> Dict[str, int]:
        """Filter for BOERE user"""
        boere_items = [item for item in items 
                      if item.page_number in range(11, 26) 
                      and not item.is_te_bestellen
                      and item.item_number.isdigit()]
        
        te_bestellen_items = [item for item in items 
                             if item.page_number in range(11, 26) 
                             and item.is_te_bestellen]
        
        return {
            'boere_count': len(boere_items),
            'te_bestellen_excluded': len(te_bestellen_items)
        }
    
    def _filter_for_accura(self, items: List[StructuredItem]) -> Dict[str, int]:
        """Filter for ACCURA user"""
        accura_items = []
        total_sides = 0
        
        for item in items:
            if item.page_number in [2, 3, 4, 5, 6, 7]:  # ACCURA pages
                sides = 0
                for side_data in [item.l1, item.l2, item.b1, item.b2]:
                    if side_data and side_data.strip() and len(side_data.strip()) > 0:
                        if side_data.upper() not in ['', 'TE BESTELLEN', 'DUMMY']:
                            sides += 1
                
                if sides > 0:
                    accura_items.append(item)
                    total_sides += sides
        
        return {
            'accura_items': len(accura_items),
            'total_sides': total_sides
        }

# Test the raw text to structured approach
if __name__ == "__main__":
    extractor = RawTextToStructured()
    
    try:
        results = extractor.extract_all_structured_data('S04479_RAPPORT_Rudi Matterne_0411_MO07202-7203_TV-wand (7-7).PDF')
        
        print("\n" + "="*60)
        print("🎯 RAW TEXT TO STRUCTURED RESULTS")
        print("="*60)
        
        print(f"📊 NESTING: {results['nesting']['total_count']} items")
        print(f"   • Nesting: {results['nesting']['nesting_count']}")
        print(f"   • Opdeelzaag: {results['nesting']['opdeelzaag_count']}")
        
        print(f"📊 BOERE: {results['boere']['boere_count']} items")
        print(f"   • Excluded Te bestellen: {results['boere']['te_bestellen_excluded']}")
        
        print(f"📊 ACCURA: {results['accura']['accura_items']} items")
        print(f"   • Total sides: {results['accura']['total_sides']}")
        
        print(f"\n📄 Files created:")
        print(f"   • structured_data.json (detailed JSON)")
        print(f"   • structured_data.csv (Excel-compatible)")
        
        # Validation
        nesting_ok = 90 <= results['nesting']['total_count'] <= 120
        boere_ok = 120 <= results['boere']['boere_count'] <= 160
        accura_ok = 60 <= results['accura']['accura_items'] <= 100
        
        print(f"\n🎯 VALIDATION:")
        print(f"   NESTING: {'✅' if nesting_ok else '❌'} {results['nesting']['total_count']} (expected ~102)")
        print(f"   BOERE: {'✅' if boere_ok else '❌'} {results['boere']['boere_count']} (expected ~144)")
        print(f"   ACCURA: {'✅' if accura_ok else '❌'} {results['accura']['accura_items']} (expected ~84)")
        
        if nesting_ok and boere_ok and accura_ok:
            print("\n🏆 STRUCTURED EXTRACTION SUCCESSFUL!")
            print("🚀 Check structured_data.csv for clean tabular data!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()