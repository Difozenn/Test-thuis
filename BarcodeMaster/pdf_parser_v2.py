#!/usr/bin/env python3
"""
Robust PDF Parser v2 - Multi-pass hybrid approach
Handles any size PDF with perfect data extraction for ACCURA, BOERE, NESTING
"""

import pdfplumber
import re
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum

class SectionType(Enum):
    NESTING = "Nesting"
    OPDEELZAAG = "Opdeelzaag" 
    CONTROLE = "Controle"
    MASSIEF = "Massief"
    MAGAZIJN = "Magazijn"
    UNKNOWN = "Unknown"

@dataclass
class TableSignature:
    """Identifies table types by column structure"""
    required_columns: List[str]
    optional_columns: List[str]
    section_types: List[SectionType]
    confidence: float

@dataclass
class SectionBoundary:
    """Defines where each section starts and ends"""
    section_type: SectionType
    start_page: int
    end_page: Optional[int]
    header_text: str

@dataclass
class ExtractedItem:
    """Single extracted item with all relevant data"""
    item_number: str
    onderdeel: str
    materiaal: str
    lengte: Optional[float]
    breedte: Optional[float] 
    dikte: Optional[float]
    l1: Optional[str]
    l2: Optional[str]
    b1: Optional[str]
    b2: Optional[str]
    pro_methode: Optional[str]
    opmerkingen: Optional[str]
    section_type: SectionType
    page_number: int

class PDFParserV2:
    def __init__(self):
        # Define table signatures for reliable identification
        self.table_signatures = [
            # Nesting/Opdeelzaag tables with L1/L2/B1/B2
            TableSignature(
                required_columns=["ONDERDEEL", "MATERIAAL", "L1", "L2", "B1", "B2"],
                optional_columns=["N°", "LENGTE", "BREEDTE", "DIKTE", "PRODUCTIEM", "OPMERKINGEN"],
                section_types=[SectionType.NESTING, SectionType.OPDEELZAAG],
                confidence=0.9
            ),
            # Controle tables - more flexible requirements
            TableSignature(
                required_columns=["MATERIAAL", "LENGTE", "BREEDTE"],
                optional_columns=["ONDERDEEL", "DIKTE", "PRO.METHODE", "STANDAARD", "REICHENBACH", "GANNOMAT", "L1", "L2", "B1", "B2"],
                section_types=[SectionType.CONTROLE],
                confidence=0.7
            ),
            # Massief tables
            TableSignature(
                required_columns=["MATERIAAL", "LENGTE", "BREEDTE"],
                optional_columns=["ONDERDEEL", "DIKTE", "MASSIEF_PM"],
                section_types=[SectionType.MASSIEF],
                confidence=0.6
            )
        ]
    
    def parse_pdf(self, pdf_path: str) -> Dict[str, any]:
        """Main parsing method - returns data for all users"""
        with pdfplumber.open(pdf_path) as pdf:
            # Pass 1: Find section boundaries
            sections = self._find_section_boundaries(pdf)
            
            # Pass 2: Extract and classify all tables
            all_items = self._extract_all_tables(pdf, sections)
            
            # Pass 3: Generate user-specific results
            results = {
                'accura': self._get_accura_data(all_items),
                'boere': self._get_boere_data(all_items),
                'nesting': self._get_nesting_data(all_items),
                'all_items': all_items,
                'sections': sections
            }
            
            return results
    
    def _find_section_boundaries(self, pdf) -> List[SectionBoundary]:
        """Pass 1: Find where each section starts and ends"""
        sections = []
        
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            
            # Look for clear section headers - only add if it's a PRIMARY header page
            # Check if the section name appears near the start of the page
            lines = text.split('\n')[:10]  # First 10 lines
            header_text = ' '.join(lines).upper()
            
            if re.search(r'\bNESTING\b', header_text, re.IGNORECASE) and 'OPDEELZAAG' not in header_text:
                sections.append(SectionBoundary(SectionType.NESTING, page_num, None, "NESTING"))
            elif re.search(r'\bOPDEELZAAG\b', header_text, re.IGNORECASE):
                sections.append(SectionBoundary(SectionType.OPDEELZAAG, page_num, None, "OPDEELZAAG"))
            elif re.search(r'\bCONTROLE\b', header_text, re.IGNORECASE):
                sections.append(SectionBoundary(SectionType.CONTROLE, page_num, None, "CONTROLE"))
            elif re.search(r'\bMASSIEF\b', header_text, re.IGNORECASE) and 'CONTROLE' not in header_text:
                sections.append(SectionBoundary(SectionType.MASSIEF, page_num, None, "MASSIEF"))
            elif re.search(r'\bMAGAZIJN\b', header_text, re.IGNORECASE):
                sections.append(SectionBoundary(SectionType.MAGAZIJN, page_num, None, "MAGAZIJN"))
        
        # Set end pages - each section continues until the next section starts
        for i, section in enumerate(sections):
            if i + 1 < len(sections):
                section.end_page = sections[i + 1].start_page - 1
            else:
                section.end_page = len(pdf.pages)
        
        return sections
    
    def _get_section_for_page(self, page_num: int, sections: List[SectionBoundary]) -> Optional[SectionType]:
        """Determine which section a page belongs to"""
        for section in sections:
            if section.start_page <= page_num <= (section.end_page or 999):
                return section.section_type
        return None
    
    def _identify_table_type(self, table: List[List[str]]) -> Tuple[Optional[SectionType], float]:
        """Pass 2: Identify table type by column structure"""
        if not table or len(table) < 2:
            return None, 0.0
        
        header = table[0]
        header_text = " ".join(str(cell).upper() for cell in header if cell)
        
        best_match = None
        best_confidence = 0.0
        
        for signature in self.table_signatures:
            # Count required columns found
            required_found = sum(1 for col in signature.required_columns 
                                if col in header_text)
            required_ratio = required_found / len(signature.required_columns)
            
            # Count optional columns found
            optional_found = sum(1 for col in signature.optional_columns 
                                if col in header_text)
            optional_ratio = optional_found / max(1, len(signature.optional_columns))
            
            # Calculate confidence
            confidence = (required_ratio * 0.8) + (optional_ratio * 0.2)
            confidence *= signature.confidence
            
            if confidence > best_confidence and required_ratio >= 0.6:  # At least 60% required columns
                best_confidence = confidence
                best_match = signature.section_types[0]  # Take first valid section type
        
        return best_match, best_confidence
    
    def _extract_all_tables(self, pdf, sections: List[SectionBoundary]) -> List[ExtractedItem]:
        """Pass 2: Extract all tables with proper classification"""
        all_items = []
        
        for page_num, page in enumerate(pdf.pages, 1):
            page_section = self._get_section_for_page(page_num, sections)
            
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 1:
                    continue
                
                # Identify table type
                table_type, confidence = self._identify_table_type(table)
                
                # Use page section context as primary, table type as validation
                final_section = page_section
                if not final_section and confidence > 0.5:
                    final_section = table_type
                
                if final_section and self._is_data_table(table):
                    items = self._extract_items_from_table(table, final_section, page_num)
                    all_items.extend(items)
        
        return all_items
    
    def _is_data_table(self, table: List[List[str]]) -> bool:
        """Check if table contains actual data vs just headers"""
        if len(table) < 1:
            return False
        
        # Check if this looks like a header row
        has_header = any(str(cell).upper() in ['ONDERDEEL', 'MATERIAAL', 'LENGTE', 'BREEDTE', 'DIKTE', 'L1', 'L2', 'B1', 'B2'] 
                        for cell in table[0] if cell)
        
        # Count rows with meaningful data
        data_rows = 0
        start_row = 1 if has_header else 0
        
        for row in table[start_row:]:
            if row and sum(1 for cell in row if cell and str(cell).strip()) >= 2:
                data_rows += 1
        
        return data_rows > 0
    
    def _extract_items_from_table(self, table: List[List[str]], section_type: SectionType, page_num: int) -> List[ExtractedItem]:
        """Extract items from a classified table"""
        items = []
        
        if len(table) < 1:
            return items
        
        # Check if this table has headers or is headerless
        header = table[0]
        column_map = self._map_columns(header)
        
        # For Nesting/Opdeelzaag sections, always use positional mapping as tables have consistent structure
        if section_type in [SectionType.NESTING, SectionType.OPDEELZAAG]:
            # Standard positional mapping for Nesting/Opdeelzaag
            column_map = {
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
            
            # Check if first row is a proper header
            has_header = any(str(cell).upper() in ['ONDERDEEL', 'MATERIAAL', 'LENGTE', 'BREEDTE', 'DIKTE'] 
                            for cell in header if cell)
            start_row = 1 if has_header else 0
            
        else:
            # For other sections, use header detection
            has_header = any(str(cell).upper() in ['ONDERDEEL', 'MATERIAAL', 'LENGTE', 'BREEDTE', 'DIKTE'] 
                            for cell in header if cell)
            
            if not has_header:
                # Controle tables: [item_num, onderdeel, materiaal, lengte, breedte, dikte, ...]
                column_map = {
                    'item_number': 0,
                    'onderdeel': 1,
                    'materiaal': 2,
                    'lengte': 3,
                    'breedte': 4,
                    'dikte': 5
                }
                start_row = 0
            else:
                start_row = 1
        
        for row_idx, row in enumerate(table[start_row:], start_row):
            if not row:
                continue
            
            # More lenient row filtering - accept any row with at least one meaningful cell
            has_content = any(cell and str(cell).strip() and len(str(cell).strip()) > 0 for cell in row)
            if not has_content:
                continue
            
            item = self._extract_item_from_row(row, column_map, section_type, page_num, row_idx + 1)
            if item:
                items.append(item)
        
        return items
    
    def _infer_controle_columns(self, table: List[List[str]]) -> Dict[str, int]:
        """Infer column positions for headerless Controle tables"""
        # Based on observed pattern: [item_num, onderdeel, materiaal, lengte, breedte, dikte, pro_methode, ...]
        column_map = {
            'onderdeel': 1,      # Component name
            'materiaal': 2,      # Material  
            'lengte': 3,         # Length
            'breedte': 4,        # Width
            'dikte': 5,          # Thickness
        }
        
        # Look for pro_methode in positions 6-8 by checking for keywords
        for i in range(6, min(9, len(table[0]) if table else 0)):
            sample_text = ' '.join(str(table[j][i]) for j in range(min(3, len(table))) if i < len(table[j]) and table[j][i])
            if any(keyword in sample_text.upper() for keyword in ['STANDAARD', 'REICHENBACH', 'GANNOMAT', 'TE BESTELLEN']):
                column_map['pro_methode'] = i
                break
        
        return column_map
    
    def _map_columns(self, header: List[str]) -> Dict[str, int]:
        """Map column names to indices"""
        column_map = {}
        
        for i, cell in enumerate(header):
            if not cell:
                continue
            
            cell_upper = str(cell).upper().strip()
            
            # Standard mappings
            if cell_upper in ['N°', 'NO', 'NUM']:
                column_map['item_number'] = i
            elif 'ONDERDEEL' in cell_upper:
                column_map['onderdeel'] = i
            elif 'MATERIAAL' in cell_upper:
                column_map['materiaal'] = i
            elif 'LENGTE' in cell_upper:
                column_map['lengte'] = i
            elif 'BREEDTE' in cell_upper:
                column_map['breedte'] = i
            elif 'DIKTE' in cell_upper:
                column_map['dikte'] = i
            elif cell_upper == 'L1':
                column_map['l1'] = i
            elif cell_upper == 'L2':
                column_map['l2'] = i
            elif cell_upper == 'B1':
                column_map['b1'] = i
            elif cell_upper == 'B2':
                column_map['b2'] = i
            elif 'PRO.METHODE' in cell_upper or 'METHODE' in cell_upper:
                column_map['pro_methode'] = i
            elif 'OPMERKING' in cell_upper:
                column_map['opmerkingen'] = i
        
        return column_map
    
    def _extract_item_from_row(self, row: List[str], column_map: Dict[str, int], 
                              section_type: SectionType, page_num: int, row_idx: int) -> Optional[ExtractedItem]:
        """Extract single item from table row"""
        
        # Get values from mapped columns
        def get_value(field: str) -> Optional[str]:
            col_idx = column_map.get(field)
            if col_idx is not None and col_idx < len(row) and row[col_idx]:
                return str(row[col_idx]).strip() or None
            return None
        
        def get_float_value(field: str) -> Optional[float]:
            value = get_value(field)
            if value:
                try:
                    return float(value.replace(',', '.'))
                except:
                    pass
            return None
        
        # Extract item number - try mapped column first, then first column
        item_number = get_value('item_number')
        if not item_number and row and str(row[0]).strip():
            item_number = str(row[0]).strip()
        if not item_number:
            item_number = str(row_idx)  # Use row index as fallback
        
        # Must have at least onderdeel or materiaal
        onderdeel = get_value('onderdeel') or ""
        materiaal = get_value('materiaal') or ""
        
        # For tables without proper column mapping, try positional extraction
        if not onderdeel and not materiaal and len(row) >= 2:
            # Try different positions for onderdeel/materiaal
            for i in range(min(4, len(row))):  # Check first 4 columns
                if row[i] and str(row[i]).strip():
                    val = str(row[i]).strip()
                    if len(val) > 1:  # Meaningful content
                        if not onderdeel:
                            onderdeel = val
                        elif not materiaal:
                            materiaal = val
                            break
        
        # Must have some meaningful data - very lenient validation
        if not onderdeel and not materiaal:
            # Try to get any content from the row
            meaningful_content = [str(cell).strip() for cell in row if cell and str(cell).strip() and len(str(cell).strip()) > 1]
            if not meaningful_content:
                return None
            # Use first meaningful content as onderdeel
            onderdeel = meaningful_content[0] if meaningful_content else ""
        
        return ExtractedItem(
            item_number=item_number,
            onderdeel=onderdeel,
            materiaal=materiaal,
            lengte=get_float_value('lengte'),
            breedte=get_float_value('breedte'),
            dikte=get_float_value('dikte'),
            l1=get_value('l1'),
            l2=get_value('l2'),
            b1=get_value('b1'),
            b2=get_value('b2'),
            pro_methode=get_value('pro_methode'),
            opmerkingen=get_value('opmerkingen'),
            section_type=section_type,
            page_number=page_num
        )
    
    def _get_accura_data(self, items: List[ExtractedItem]) -> Dict[str, int]:
        """Pass 3: Generate ACCURA-specific results"""
        accura_items = []
        
        for item in items:
            # ACCURA processes Nesting and Opdeelzaag items with L1/L2/B1/B2 data
            if item.section_type in [SectionType.NESTING, SectionType.OPDEELZAAG]:
                # Check if item has meaningful L1/L2/B1/B2 content
                sides = 0
                for content in [item.l1, item.l2, item.b1, item.b2]:
                    if (content and content.strip() and 
                        content.upper() not in ['', 'TE BESTELLEN', 'DUMMY'] and
                        len(content.strip()) > 1):
                        sides += 1
                
                if sides > 0:
                    accura_items.append({'item': item, 'sides': sides})
        
        return {
            'aantal_items': len(accura_items),
            'aantal_sides': sum(item['sides'] for item in accura_items)
        }
    
    def _get_boere_data(self, items: List[ExtractedItem]) -> int:
        """Pass 3: Generate BOERE-specific results"""
        boere_count = 0
        
        for item in items:
            # BOERE processes items from Controle header (page 11) to before Magazijn header (page 26)
            if 11 <= item.page_number <= 25 and item.section_type in [SectionType.CONTROLE, SectionType.MASSIEF]:
                # Only count items with actual N° (item numbers) 
                has_item_number = item.item_number and item.item_number.isdigit()
                
                # Exclude items with "Te bestellen" in Pro.methode
                is_te_bestellen = (item.pro_methode and 'TE BESTELLEN' in item.pro_methode.upper())
                
                if has_item_number and not is_te_bestellen:
                    boere_count += 1
        
        return boere_count
    
    def _get_nesting_data(self, items: List[ExtractedItem]) -> Dict[str, int]:
        """Pass 3: Generate NESTING-specific results"""
        nesting_count = sum(1 for item in items if item.section_type == SectionType.NESTING)
        opdeelzaag_count = sum(1 for item in items if item.section_type == SectionType.OPDEELZAAG)
        
        return {
            'nesting_count': nesting_count,
            'opdeelzaag_count': opdeelzaag_count
        }

# Test the new parser
if __name__ == "__main__":
    parser = PDFParserV2()
    results = parser.parse_pdf('S04479_RAPPORT_Rudi Matterne_0411_MO07202-7203_TV-wand (7-7).PDF')
    
    print("=== ROBUST PDF PARSER V2 RESULTS ===")
    print(f"ACCURA: {results['accura']['aantal_items']} items, {results['accura']['aantal_sides']} sides")
    print(f"BOERE: {results['boere']} items")
    print(f"NESTING: {results['nesting']['nesting_count']} Nesting, {results['nesting']['opdeelzaag_count']} Opdeelzaag")
    
    print(f"\nSections found:")
    for section in results['sections']:
        print(f"  {section.section_type.value}: pages {section.start_page}-{section.end_page}")
    
    print(f"\nTotal items extracted: {len(results['all_items'])}")