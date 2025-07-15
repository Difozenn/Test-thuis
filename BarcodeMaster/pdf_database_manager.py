#!/usr/bin/env python3
"""
PDF Database Manager for BarcodeMaster
Parses PDFs once and stores structured table data in database
"""

import sqlite3
import json
import logging
import os
from datetime import datetime
import traceback
import pdfplumber
import re
from path_utils import get_writable_path

class PDFDatabaseManager:
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.logger = logging.getLogger(__name__)
        # Use absolute path for database
        self.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pdf_cache.db')
        self._init_database()
    
    def _log(self, message):
        """Log message to both logger and callback."""
        self.logger.info(message)
        if self.log_callback:
            self.log_callback(message)
    
    def _init_database(self):
        """Initialize PDF cache database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS pdf_documents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        filename TEXT UNIQUE,
                        project_code TEXT,
                        so_number TEXT,
                        file_size INTEGER,
                        file_modified TIMESTAMP,
                        parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        total_pages INTEGER,
                        parse_success BOOLEAN DEFAULT 0
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS pdf_table_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pdf_id INTEGER,
                        page_number INTEGER,
                        section_type TEXT,
                        table_index INTEGER,
                        row_number INTEGER,
                        item_number TEXT,
                        onderdeel TEXT,
                        materiaal TEXT,
                        lengte REAL,
                        breedte REAL,
                        dikte REAL,
                        l1 TEXT,
                        l2 TEXT,
                        b1 TEXT,
                        b2 TEXT,
                        pro_methode TEXT,
                        opmerkingen TEXT,
                        raw_data TEXT,
                        FOREIGN KEY (pdf_id) REFERENCES pdf_documents(id)
                    )
                ''')
                
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_pdf_project ON pdf_documents(project_code)
                ''')
                
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_table_section ON pdf_table_data(pdf_id, section_type)
                ''')
                
                conn.commit()
                self._log("PDF database initialized successfully")
                
        except Exception as e:
            self._log(f"Error initializing PDF database: {e}")
            raise
    
    def is_pdf_cached(self, pdf_path, project_code):
        """Check if PDF is already cached and up to date."""
        try:
            if not os.path.exists(pdf_path):
                return False
            
            file_size = os.path.getsize(pdf_path)
            file_modified = datetime.fromtimestamp(os.path.getmtime(pdf_path))
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT id, parse_success FROM pdf_documents 
                    WHERE filename = ? AND file_size = ? AND file_modified = ?
                ''', (pdf_path, file_size, file_modified))
                
                row = cursor.fetchone()
                if row and row[1]:  # parse_success = 1
                    self._log(f"PDF already cached: {pdf_path}")
                    return True
                    
            return False
            
        except Exception as e:
            self._log(f"Error checking PDF cache: {e}")
            return False
    
    def parse_and_store_pdf(self, pdf_path, project_code, so_number=None):
        """Parse PDF and store all table data in database."""
        try:
            self._log(f"Parsing and storing PDF: {pdf_path}")
            
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF not found: {pdf_path}")
            
            file_size = os.path.getsize(pdf_path)
            file_modified = datetime.fromtimestamp(os.path.getmtime(pdf_path))
            
            # Extract SO number from filename if not provided
            if not so_number:
                filename = os.path.basename(pdf_path)
                match = re.search(r'^(S\d+)', filename, re.IGNORECASE)
                if match:
                    so_number = match.group(1).upper()
            
            # Store PDF document record
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    INSERT OR REPLACE INTO pdf_documents 
                    (filename, project_code, so_number, file_size, file_modified, total_pages, parse_success)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (pdf_path, project_code, so_number, file_size, file_modified, 0, 0))
                
                pdf_id = cursor.lastrowid
                conn.commit()
            
            # Parse PDF content
            total_rows_stored = 0
            
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                
                for page_num, page in enumerate(pdf.pages, 1):
                    self._log(f"Processing page {page_num}/{total_pages}")
                    
                    # Detect section type from page text
                    page_text = page.extract_text() or ""
                    section_type = self._detect_section_type(page_text)
                    
                    if not section_type:
                        continue
                    
                    # Extract tables with improved settings
                    tables = self._extract_tables_with_settings(page)
                    
                    for table_idx, table in enumerate(tables):
                        if not table or len(table) < 2:
                            continue
                        
                        rows_stored = self._process_table(pdf_id, page_num, section_type, table_idx, table)
                        total_rows_stored += rows_stored
                
                # Update document with success status
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('''
                        UPDATE pdf_documents 
                        SET total_pages = ?, parse_success = 1 
                        WHERE id = ?
                    ''', (total_pages, pdf_id))
                    conn.commit()
                
                self._log(f"Successfully stored {total_rows_stored} rows from {total_pages} pages")
                return True
                
        except Exception as e:
            self._log(f"Error parsing PDF {pdf_path}: {e}")
            self._log(traceback.format_exc())
            return False
    
    def _detect_section_type(self, page_text):
        """Detect section type from page text."""
        text_upper = page_text.upper()
        
        if 'NESTING' in text_upper:
            return 'Nesting'
        elif 'OPDEELZAAG' in text_upper:
            return 'Opdeelzaag'
        elif 'CONTROLE' in text_upper:
            return 'Controle'
        elif 'MASSIEF' in text_upper:
            return 'Massief'
        elif 'MAGAZIJN' in text_upper:
            return 'Magazijn'
        
        return None
    
    def _extract_tables_with_settings(self, page):
        """Extract tables with optimized settings."""
        try:
            # Try multiple table extraction strategies
            strategies = [
                # Default strategy
                {},
                # Relaxed vertical tolerance
                {"vertical_strategy": "text", "horizontal_strategy": "text"},
                # Explicit line detection
                {"explicit_vertical_lines": True, "explicit_horizontal_lines": True},
                # Edge detection
                {"edge_min_length": 3, "snap_tolerance": 3}
            ]
            
            for strategy in strategies:
                try:
                    tables = page.extract_tables(table_settings=strategy)
                    if tables and any(len(table) > 1 for table in tables):
                        return tables
                except:
                    continue
            
            # Fallback: try without table settings
            return page.extract_tables()
            
        except Exception as e:
            self._log(f"Error extracting tables: {e}")
            return []
    
    def _process_table(self, pdf_id, page_num, section_type, table_idx, table):
        """Process and store table data."""
        rows_stored = 0
        
        try:
            if not table or len(table) < 2:
                return 0
            
            # Get header row
            header = table[0]
            if not header:
                return 0
            
            # Log header for debugging
            self._log(f"Table {table_idx} header: {header}")
            
            # Map column names to indices
            column_map = self._map_columns(header)
            self._log(f"Column mapping: {column_map}")
            
            # Process data rows
            with sqlite3.connect(self.db_path) as conn:
                for row_idx, row in enumerate(table[1:], 1):
                    if not row:
                        continue
                    
                    # Extract data using column mapping
                    row_data = self._extract_row_data(row, column_map)
                    
                    # For numbered rows, try to extract item number from first column if not mapped
                    if 'item_number' not in row_data and row and str(row[0]).strip().isdigit():
                        row_data['item_number'] = str(row[0]).strip()
                    
                    # Skip rows without item numbers for main data tables
                    if section_type in ['Nesting', 'Opdeelzaag', 'Controle'] and not row_data.get('item_number'):
                        continue
                    
                    # Store row in database
                    conn.execute('''
                        INSERT INTO pdf_table_data (
                            pdf_id, page_number, section_type, table_index, row_number,
                            item_number, onderdeel, materiaal, lengte, breedte, dikte,
                            l1, l2, b1, b2, pro_methode, opmerkingen, raw_data
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        pdf_id, page_num, section_type, table_idx, row_idx,
                        row_data.get('item_number'),
                        row_data.get('onderdeel'),
                        row_data.get('materiaal'),
                        row_data.get('lengte'),
                        row_data.get('breedte'),
                        row_data.get('dikte'),
                        row_data.get('l1'),
                        row_data.get('l2'),
                        row_data.get('b1'),
                        row_data.get('b2'),
                        row_data.get('pro_methode'),
                        row_data.get('opmerkingen'),
                        json.dumps(row)
                    ))
                    
                    rows_stored += 1
                
                conn.commit()
            
            self._log(f"Stored {rows_stored} rows from {section_type} table {table_idx} on page {page_num}")
            return rows_stored
            
        except Exception as e:
            self._log(f"Error processing table: {e}")
            return 0
    
    def _map_columns(self, header):
        """Map column names to their indices."""
        column_map = {}
        
        for i, cell in enumerate(header):
            if not cell:
                continue
            
            cell_upper = str(cell).upper().strip()
            
            # Map common column names
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
    
    def _extract_row_data(self, row, column_map):
        """Extract row data using column mapping."""
        row_data = {}
        
        for field, col_idx in column_map.items():
            try:
                if col_idx < len(row) and row[col_idx]:
                    value = str(row[col_idx]).strip()
                    
                    # Convert numeric fields
                    if field in ['lengte', 'breedte', 'dikte']:
                        try:
                            row_data[field] = float(value.replace(',', '.'))
                        except:
                            row_data[field] = None
                    else:
                        row_data[field] = value if value else None
                else:
                    row_data[field] = None
            except Exception as e:
                row_data[field] = None
        
        return row_data
    
    def get_accura_data(self, project_code):
        """Get ACCURA data for a project."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT item_number, onderdeel, l1, l2, b1, b2, section_type
                    FROM pdf_table_data ptd
                    JOIN pdf_documents pd ON ptd.pdf_id = pd.id
                    WHERE pd.project_code = ? 
                    AND ptd.section_type IN ('Nesting', 'Opdeelzaag')
                    AND ptd.item_number IS NOT NULL
                    ORDER BY ptd.section_type, CAST(ptd.item_number AS INTEGER)
                ''', (project_code,))
                
                rows = cursor.fetchall()
                
                aantal_items = 0
                aantal_sides = 0
                
                for row in rows:
                    item_num, onderdeel, l1, l2, b1, b2, section = row
                    
                    # Count meaningful content in L1/L2/B1/B2 columns
                    sides_in_row = 0
                    for content in [l1, l2, b1, b2]:
                        if (content and content.strip() and 
                            content.upper() not in ['', 'TE BESTELLEN', 'DUMMY', 'N/A'] and
                            not content.isdigit() and len(content.strip()) > 1):
                            sides_in_row += 1
                    
                    if sides_in_row > 0:
                        aantal_items += 1
                        aantal_sides += sides_in_row
                        self._log(f"ACCURA {section} item {item_num}: {sides_in_row} sides")
                
                self._log(f"ACCURA database result: {aantal_items} items, {aantal_sides} sides")
                return {'aantal_items': aantal_items, 'aantal_sides': aantal_sides}
                
        except Exception as e:
            self._log(f"Error getting ACCURA data: {e}")
            return {'aantal_items': 0, 'aantal_sides': 0}
    
    def get_boere_data(self, project_code):
        """Get BOERE data for a project (excluding 'Te bestellen')."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT item_number, onderdeel, pro_methode
                    FROM pdf_table_data ptd
                    JOIN pdf_documents pd ON ptd.pdf_id = pd.id
                    WHERE pd.project_code = ? 
                    AND ptd.section_type = 'Controle'
                    AND ptd.item_number IS NOT NULL
                    AND (ptd.pro_methode IS NULL OR UPPER(ptd.pro_methode) NOT LIKE '%TE BESTELLEN%')
                    ORDER BY CAST(ptd.item_number AS INTEGER)
                ''', (project_code,))
                
                rows = cursor.fetchall()
                item_count = len(rows)
                
                for row in rows:
                    item_num, onderdeel, pro_methode = row
                    self._log(f"BOERE item {item_num}: {onderdeel} - Pro.methode: {pro_methode}")
                
                self._log(f"BOERE database result: {item_count} items (excluding 'Te bestellen')")
                return item_count
                
        except Exception as e:
            self._log(f"Error getting BOERE data: {e}")
            return 0
    
    def get_nesting_data(self, project_code):
        """Get NESTING data for a project."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get Nesting count
                cursor = conn.execute('''
                    SELECT COUNT(*) FROM pdf_table_data ptd
                    JOIN pdf_documents pd ON ptd.pdf_id = pd.id
                    WHERE pd.project_code = ? 
                    AND ptd.section_type = 'Nesting'
                    AND ptd.item_number IS NOT NULL
                ''', (project_code,))
                nesting_count = cursor.fetchone()[0]
                
                # Get Opdeelzaag count
                cursor = conn.execute('''
                    SELECT COUNT(*) FROM pdf_table_data ptd
                    JOIN pdf_documents pd ON ptd.pdf_id = pd.id
                    WHERE pd.project_code = ? 
                    AND ptd.section_type = 'Opdeelzaag'
                    AND ptd.item_number IS NOT NULL
                ''', (project_code,))
                opdeelzaag_count = cursor.fetchone()[0]
                
                self._log(f"NESTING database result: Nesting={nesting_count}, Opdeelzaag={opdeelzaag_count}")
                return {'nesting_count': nesting_count, 'opdeelzaag_count': opdeelzaag_count}
                
        except Exception as e:
            self._log(f"Error getting NESTING data: {e}")
            return {'nesting_count': 0, 'opdeelzaag_count': 0}
    
    def get_so_number_for_project(self, project_code):
        """Get SO number for a project code."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT so_number FROM pdf_documents 
                    WHERE project_code = ?
                    LIMIT 1
                ''', (project_code,))
                
                row = cursor.fetchone()
                if row and row[0]:
                    return row[0]
                
                return None
                
        except Exception as e:
            self._log(f"Error getting SO number: {e}")
            return None