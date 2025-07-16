#!/usr/bin/env python3
"""
Dynamic Column Parser - Uses header positions to define column boundaries
"""

import pdfplumber
import re
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

@dataclass
class ColumnDefinition:
    """Column definition based on header position"""
    name: str
    x_start: float
    x_end: float

@dataclass
class ExtractedRow:
    """Extracted row with proper column alignment"""
    page_num: int
    columns: Dict[str, str]  # column_name -> cell_value

class DynamicColumnParser:
    def __init__(self):
        pass
    
    def extract_boere_count(self, pdf_path: str) -> int:
        """Extract BOERE count using dynamic column detection"""
        
        total_count = 0
        
        with pdfplumber.open(pdf_path) as pdf:
            # Process pages 11-25 (Controle to Magazijn)
            for page_num in range(11, 26):
                page = pdf.pages[page_num-1]
                
                # Find column definitions for this page
                column_defs = self._detect_columns_from_headers(page)
                
                if column_defs:
                    # Extract data rows using these column definitions
                    data_rows = self._extract_data_rows(page, column_defs, page_num)
                    
                    # Count valid BOERE items
                    page_count = 0
                    for row in data_rows:
                        item_number = row.columns.get('N°', '').strip()
                        pro_methode = row.columns.get('Pro.methode', '').strip()
                        
                        # Count if has digit N° and not "Te bestellen"
                        if item_number.isdigit() and 'TE BESTELLEN' not in pro_methode.upper():
                            page_count += 1
                    
                    total_count += page_count
                    print(f"Page {page_num}: {page_count} items (columns: {list(column_defs.keys())})")
                else:
                    print(f"Page {page_num}: No valid columns detected")
        
        return total_count
    
    def _detect_columns_from_headers(self, page) -> Dict[str, ColumnDefinition]:
        """Detect column positions by finding header text"""
        
        # Get all characters
        chars = page.chars
        
        # Known header names we're looking for
        header_names = ['N°', 'Onderdeel', 'Materiaal', 'Lengte', 'Breedte', 'Dikte', 
                       'Pro.methode', 'L1', 'L2', 'B1', 'B2', 'commentaar']
        
        found_headers = {}
        
        # Look for header text in characters
        for header in header_names:
            header_chars = self._find_text_in_chars(chars, header)
            if header_chars:
                # Calculate column boundaries
                x_start = min(c['x0'] for c in header_chars)
                x_end = max(c['x1'] for c in header_chars)
                
                found_headers[header] = ColumnDefinition(
                    name=header,
                    x_start=x_start,
                    x_end=x_end
                )
        
        # Extend column boundaries to prevent gaps
        if found_headers:
            found_headers = self._adjust_column_boundaries(found_headers)
        
        return found_headers
    
    def _find_text_in_chars(self, chars: List[dict], target_text: str) -> List[dict]:
        """Find characters that form the target text"""
        
        # Look for exact matches first
        for i in range(len(chars) - len(target_text) + 1):
            sequence = ''.join([chars[j]['text'] for j in range(i, i + len(target_text))])
            if sequence == target_text:
                return chars[i:i + len(target_text)]
        
        # Look for partial matches (for cases like "Pro.methode" might be split)
        target_clean = target_text.replace('.', '').replace('°', '')
        for i in range(len(chars) - len(target_clean) + 1):
            sequence = ''.join([chars[j]['text'] for j in range(i, i + len(target_clean))])
            sequence_clean = sequence.replace('.', '').replace('°', '')
            if sequence_clean == target_clean:
                return chars[i:i + len(target_clean)]
        
        return []
    
    def _adjust_column_boundaries(self, headers: Dict[str, ColumnDefinition]) -> Dict[str, ColumnDefinition]:
        """Adjust column boundaries to prevent gaps and overlaps"""
        
        # Sort columns by x position
        sorted_headers = sorted(headers.items(), key=lambda x: x[1].x_start)
        
        adjusted = {}
        
        for i, (name, col_def) in enumerate(sorted_headers):
            x_start = col_def.x_start
            
            # Extend to previous column's end
            if i > 0:
                prev_end = sorted_headers[i-1][1].x_end
                x_start = min(x_start, prev_end + 1)
            
            # Extend to next column's start
            if i < len(sorted_headers) - 1:
                next_start = sorted_headers[i+1][1].x_start
                x_end = (col_def.x_end + next_start) / 2  # Midpoint
            else:
                x_end = col_def.x_end + 100  # Extend last column
            
            adjusted[name] = ColumnDefinition(
                name=name,
                x_start=x_start,
                x_end=x_end
            )
        
        return adjusted
    
    def _extract_data_rows(self, page, column_defs: Dict[str, ColumnDefinition], page_num: int) -> List[ExtractedRow]:
        """Extract data rows using column definitions"""
        
        chars = page.chars
        
        # Group characters by Y position (rows)
        rows_dict = {}
        for char in chars:
            y_rounded = round(char['y0'])
            if y_rounded not in rows_dict:
                rows_dict[y_rounded] = []
            rows_dict[y_rounded].append(char)
        
        data_rows = []
        
        # Process each row
        for y_pos in sorted(rows_dict.keys(), reverse=True):  # Top to bottom
            row_chars = rows_dict[y_pos]
            
            # Skip header rows and empty rows
            row_text = ''.join([c['text'] for c in sorted(row_chars, key=lambda x: x['x0'])])
            if self._is_header_or_empty_row(row_text):
                continue
            
            # Extract data for each column
            row_data = {}
            for col_name, col_def in column_defs.items():
                # Get characters in this column
                col_chars = [c for c in row_chars 
                           if col_def.x_start <= c['x0'] < col_def.x_end]
                
                # Combine into cell text
                if col_chars:
                    cell_text = ''.join([c['text'] for c in sorted(col_chars, key=lambda x: x['x0'])])
                    row_data[col_name] = cell_text.strip()
                else:
                    row_data[col_name] = ""
            
            # Only include rows with meaningful data
            if any(row_data.values()) and self._is_data_row(row_data):
                data_rows.append(ExtractedRow(page_num=page_num, columns=row_data))
        
        return data_rows
    
    def _is_header_or_empty_row(self, row_text: str) -> bool:
        """Check if row is a header or should be skipped"""
        row_text = row_text.strip()
        
        skip_patterns = ['N°', 'Onderdeel', 'Materiaal', 'Lengte', 'Breedte', 'Dikte',
                        'Pro.methode', 'L1', 'L2', 'B1', 'B2', 'commentaar',
                        'Aantal onderdelen:', 'Commentaar:', 'Br:', 'MONTEREN', 
                        '0411_MO07202', 'Page', 'Fineer', 'eik', '1mm']
        
        return not row_text or any(pattern in row_text for pattern in skip_patterns)
    
    def _is_data_row(self, row_data: Dict[str, str]) -> bool:
        """Check if row contains actual component data"""
        
        # Must have either a digit in N° or a component name in Onderdeel
        item_number = row_data.get('N°', '').strip()
        onderdeel = row_data.get('Onderdeel', '').strip()
        
        has_number = bool(re.search(r'\\d', item_number))
        has_component = len(onderdeel) > 1 and not onderdeel.isdigit()
        
        return has_number or has_component

# Test the dynamic parser
if __name__ == "__main__":
    parser = DynamicColumnParser()
    
    print("=== DYNAMIC COLUMN PARSER TEST ===")
    boere_count = parser.extract_boere_count('S04479_RAPPORT_Rudi Matterne_0411_MO07202-7203_TV-wand (7-7).PDF')
    
    print(f"\\n=== FINAL RESULT ===")
    print(f"BOERE count (dynamic columns): {boere_count}")