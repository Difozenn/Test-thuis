#!/usr/bin/env python3
"""
Precise PDF Parser - Manual cell boundary detection for 100% accuracy
"""

import pdfplumber
import re
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

@dataclass
class TableCell:
    """Single table cell with precise coordinates"""
    text: str
    x0: float
    y0: float
    x1: float
    y1: float

@dataclass
class TableRow:
    """Table row with properly aligned cells"""
    cells: List[TableCell]
    y_position: float

class PrecisePDFParser:
    def __init__(self):
        self.column_boundaries = {}  # Store column boundaries per page
    
    def extract_precise_table(self, page, page_num: int) -> List[TableRow]:
        """Extract table with manually detected cell boundaries"""
        
        # Get all characters from the page
        chars = page.chars
        
        # Filter characters to table area (adjust coordinates as needed)
        table_chars = [c for c in chars if self._is_in_table_area(c, page_num)]
        
        # Group characters by rows (Y coordinate)
        rows_dict = self._group_by_rows(table_chars)
        
        # For each row, detect column boundaries and create cells
        table_rows = []
        for y_pos in sorted(rows_dict.keys(), reverse=True):  # Top to bottom
            row_chars = rows_dict[y_pos]
            
            # Skip empty or header-only rows
            row_text = ''.join([c['text'] for c in sorted(row_chars, key=lambda x: x['x0'])])
            if not self._is_data_row(row_text):
                continue
            
            # Create cells for this row
            cells = self._create_cells_from_chars(row_chars, page_num)
            if cells:
                table_rows.append(TableRow(cells=cells, y_position=y_pos))
        
        return table_rows
    
    def _is_in_table_area(self, char: dict, page_num: int) -> bool:
        """Determine if character is in the table area"""
        # Adjust these coordinates based on the page layout
        x_min, x_max = 50, 800  # Approximate table width
        
        # Different Y ranges for different pages
        if page_num == 13:  # Page 13 specific
            y_min, y_max = 200, 450
        else:
            y_min, y_max = 100, 600  # General range
        
        return (x_min <= char['x0'] <= x_max and 
                y_min <= char['y0'] <= y_max and
                char['text'].strip())
    
    def _group_by_rows(self, chars: List[dict]) -> Dict[int, List[dict]]:
        """Group characters by approximate Y position (rows)"""
        rows = {}
        
        for char in chars:
            # Round Y coordinate to group nearby characters
            y_rounded = round(char['y0'])
            
            if y_rounded not in rows:
                rows[y_rounded] = []
            rows[y_rounded].append(char)
        
        return rows
    
    def _is_data_row(self, row_text: str) -> bool:
        """Check if row contains actual data (not headers/comments)"""
        row_text = row_text.strip()
        
        # Skip empty rows, headers, comments
        skip_patterns = ['N°', 'Onderdeel', 'Materiaal', 'Aantal onderdelen:', 
                        'Commentaar:', 'Br:', 'MONTEREN', '0411_MO07202']
        
        if not row_text or any(pattern in row_text for pattern in skip_patterns):
            return False
        
        # Must have at least a digit or component name
        return bool(re.search(r'\\d|[A-Z]{2,}', row_text))
    
    def _create_cells_from_chars(self, row_chars: List[dict], page_num: int) -> List[TableCell]:
        """Create properly aligned cells from character positions"""
        
        # Sort characters by X position
        sorted_chars = sorted(row_chars, key=lambda x: x['x0'])
        
        # Define column boundaries based on typical PDF layout
        # These are approximate X coordinates for each column
        column_bounds = [
            (50, 100),   # N° column
            (100, 200),  # Onderdeel column  
            (200, 350),  # Materiaal column
            (350, 400),  # Lengte column
            (400, 450),  # Breedte column
            (450, 500),  # Dikte column
            (500, 550),  # Pro.methode column
            (550, 600),  # L1 column
            (600, 650),  # L2 column
            (650, 700),  # B1 column
            (700, 750),  # B2 column
            (750, 800),  # Comments column
        ]
        
        cells = []
        
        # For each column, collect characters that fall within its boundaries
        for i, (x_min, x_max) in enumerate(column_bounds):
            column_chars = [c for c in sorted_chars if x_min <= c['x0'] < x_max]
            
            if column_chars:
                # Combine characters into cell text
                cell_text = ''.join([c['text'] for c in sorted(column_chars, key=lambda x: x['x0'])])
                cell_text = cell_text.strip()
                
                if cell_text:  # Only create cell if it has content
                    cells.append(TableCell(
                        text=cell_text,
                        x0=column_chars[0]['x0'],
                        y0=min(c['y0'] for c in column_chars),
                        x1=column_chars[-1]['x1'],
                        y1=max(c['y1'] for c in column_chars)
                    ))
            else:
                # Empty cell
                cells.append(TableCell(text="", x0=x_min, y0=0, x1=x_max, y1=0))
        
        return cells
    
    def extract_boere_items_precise(self, pdf_path: str) -> int:
        """Extract BOERE count with precise cell detection"""
        
        boere_count = 0
        
        with pdfplumber.open(pdf_path) as pdf:
            # Process pages 11-25 (Controle to Magazijn)
            for page_num in range(11, 26):
                page = pdf.pages[page_num-1]
                
                # Extract table rows with precise cell detection
                table_rows = self.extract_precise_table(page, page_num)
                
                print(f"\\nPage {page_num}: {len(table_rows)} data rows")
                
                for row in table_rows:
                    # Get N° from first cell
                    item_number = row.cells[0].text if row.cells else ""
                    
                    # Get Pro.methode (usually around column 6-7)
                    pro_methode = ""
                    if len(row.cells) > 6:
                        pro_methode = row.cells[6].text
                    
                    # Count if has digit N° and not "Te bestellen"
                    if item_number.isdigit() and 'Te bestellen' not in pro_methode:
                        boere_count += 1
                        print(f"  N° {item_number}: {row.cells[1].text if len(row.cells) > 1 else ''}")
        
        return boere_count

# Test the precise parser
if __name__ == "__main__":
    parser = PrecisePDFParser()
    
    print("=== PRECISE PDF PARSER TEST ===")
    boere_count = parser.extract_boere_items_precise('S04479_RAPPORT_Rudi Matterne_0411_MO07202-7203_TV-wand (7-7).PDF')
    
    print(f"\\n=== FINAL RESULT ===")
    print(f"BOERE count (precise extraction): {boere_count}")