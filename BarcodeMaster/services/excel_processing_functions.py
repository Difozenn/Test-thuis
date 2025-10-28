"""
Excel Processing Functions for BarcodeMaster
Handles NESTING, ACCURA, and BOERE processing from Excel files
"""

import os
import re
import pandas as pd
from datetime import datetime
import traceback

# Optional Excel writing dependencies
try:
    import xlwt
    HAS_XLW = True
except ImportError:
    HAS_XLW = False

try:
    import xlsxwriter  
    HAS_XLSXWRITER = True
except ImportError:
    HAS_XLSXWRITER = False


def find_header_row(excel_path, sheet_name):
    """
    Find the row containing the actual data headers in the Excel file.
    
    Args:
        excel_path: Path to Excel file
        sheet_name: Name of sheet to read
        
    Returns:
        int: Row number (0-indexed) where headers are found, or 0 if not found
    """
    try:
        # Read raw data without headers
        df_raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)
        
        # Look for rows containing our expected column names
        expected_columns = ['Parcours', 'Materiaal', 'Afplak Boven', 'Afplak Onder', 'Afplak Links', 'Afplak Rechts']
        
        for i in range(min(15, len(df_raw))):  # Check first 15 rows
            row_values = [str(df_raw.iloc[i, j]) if pd.notna(df_raw.iloc[i, j]) else '' for j in range(len(df_raw.columns))]
            row_str = ' | '.join(row_values)
            
            # Check if this row contains multiple expected columns
            matches = sum(1 for col in expected_columns if col in row_str)
            if matches >= 3:  # If we find at least 3 expected columns
                print(f"[HEADER_DETECTION] Found header row at row {i}")
                return i
        
        print("[HEADER_DETECTION] No header row found, using row 0")
        return 0
        
    except Exception as e:
        print(f"[HEADER_DETECTION] Error finding header row: {e}")
        return 0


def get_sheet_name(excel_path):
    """
    Get the correct sheet name to use for processing.
    Tries common sheet names and returns the first one found.
    
    Args:
        excel_path: Path to Excel file
        
    Returns:
        sheet_name: Name of sheet to use, or None if none found
    """
    try:
        # Try common sheet names in order of preference
        common_names = ['1 PLATEN', '1_PLATEN', 'PageStyle_1 PLATEN', 'PLATEN', 'Sheet1', 'Blad1']
        
        # Get available sheet names
        excel_file = pd.ExcelFile(excel_path)
        available_sheets = excel_file.sheet_names
        
        print(f"[SHEET_DETECTION] Available sheets in {os.path.basename(excel_path)}: {available_sheets}")
        
        # Try each common name
        for sheet_name in common_names:
            if sheet_name in available_sheets:
                print(f"[SHEET_DETECTION] Using sheet: {sheet_name}")
                return sheet_name
        
        # Try pattern matching for PageStyle_X PLATEN variants
        for sheet_name in available_sheets:
            if re.match(r'PageStyle_\d+\s+PLATEN', sheet_name, re.IGNORECASE):
                print(f"[SHEET_DETECTION] Using PageStyle pattern sheet: {sheet_name}")
                return sheet_name
        
        # If no common name found, use first available sheet
        if available_sheets:
            sheet_name = available_sheets[0]
            print(f"[SHEET_DETECTION] Using first available sheet: {sheet_name}")
            return sheet_name
            
        print(f"[SHEET_DETECTION] No sheets found in {excel_path}")
        return None
        
    except Exception as e:
        print(f"[SHEET_DETECTION] Error getting sheet name (missing xlrd?): {e}")
        # Default to '1 PLATEN' if sheet detection fails
        print(f"[SHEET_DETECTION] Defaulting to '1 PLATEN' sheet")
        return '1 PLATEN'


def extract_color_from_excel(excel_path, sheet_name):
    """
    Extract color information from Excel file header section.
    The color is typically in the first few rows, after 'Kleur: '.
    
    Args:
        excel_path: Path to Excel file
        sheet_name: Name of sheet to read
        
    Returns:
        str: Color value or None if not found
    """
    try:
        # Read the header section (first 10 rows) without processing
        df_header = pd.read_excel(excel_path, sheet_name=sheet_name, header=None, nrows=10)
        
        # Look for "Kleur:" in the header section
        for i in range(len(df_header)):
            for j in range(len(df_header.columns)):
                cell_value = df_header.iloc[i, j]
                if pd.notna(cell_value) and 'Kleur' in str(cell_value):
                    # Found "Kleur:" - look for color value in adjacent cells
                    # Check next column
                    if j + 1 < len(df_header.columns):
                        color_value = df_header.iloc[i, j + 1]
                        if pd.notna(color_value) and str(color_value).strip():
                            color_str = str(color_value).strip()
                            print(f"[COLOR] Found color: {color_str}")
                            return color_str
                    
                    # Check same row, different columns
                    for k in range(j + 1, min(j + 5, len(df_header.columns))):
                        color_value = df_header.iloc[i, k]
                        if pd.notna(color_value) and str(color_value).strip():
                            color_str = str(color_value).strip()
                            if not color_str.startswith('Unnamed'):
                                print(f"[COLOR] Found color: {color_str}")
                                return color_str
                    
        print("[COLOR] No color found in header section")
        return None
        
    except Exception as e:
        print(f"[COLOR] Error extracting color: {e}")
        return None


def find_excel_file_for_project(directory, project_code):
    """
    Find Excel file matching the project code.
    
    Args:
        directory: Directory to search in
        project_code: Project code like "MO06789_Hangkastjes_(7-16)"
        
    Returns:
        Full path to matching Excel file or None
    """
    try:
        print(f"[EXCEL_MATCH] Looking for project '{project_code}' in directory '{directory}'")
        
        # Debug: show what we're searching in
        print(f"[EXCEL_MATCH] Debug - searching for MO pattern in: {repr(project_code)}")
        print(f"[EXCEL_MATCH] Debug - uppercase version: {project_code.upper()}")
        
        # Extract just the MO code if present
        mo_match = re.search(r'(MO\d{4,5})', project_code, re.IGNORECASE)
        if mo_match:
            mo_code = mo_match.group(1).upper()
            print(f"[EXCEL_MATCH] Regex matched: '{mo_code}'")
        else:
            mo_code = project_code.upper()
            print(f"[EXCEL_MATCH] No regex match, using full string")
        
        print(f"[EXCEL_MATCH] Extracted MO code: '{mo_code}'")
        
        # Search for Excel files in directory
        exact_match = None
        mo_code_matches = []
        
        for filename in os.listdir(directory):
            if filename.endswith(('.xlsx', '.xls')):
                print(f"[EXCEL_MATCH] Checking file: '{filename}'")
                
                # Check if MO code is in filename
                if mo_code in filename.upper():
                    print(f"[EXCEL_MATCH] MO code '{mo_code}' found in filename")
                    
                    # Check if the full project code pattern matches
                    if project_code.upper() in filename.upper():
                        print(f"[EXCEL_MATCH] ✓ Full project code '{project_code}' matches filename '{filename}'")
                        exact_match = os.path.join(directory, filename)
                        break  # Found exact match, stop searching
                    else:
                        # Store MO code match for fallback
                        mo_code_matches.append((filename, os.path.join(directory, filename)))
                        print(f"[EXCEL_MATCH] MO code match stored for fallback: '{filename}'")
                else:
                    print(f"[EXCEL_MATCH] MO code '{mo_code}' not found in '{filename}'")
        
        # Return exact match if found
        if exact_match:
            return exact_match
            
        # If no exact match, try to find the best MO code match
        if mo_code_matches:
            # Try to find a match that contains more of the project code
            best_match = None
            best_score = 0
            
            for filename, filepath in mo_code_matches:
                # Calculate how much of the project code matches
                # Remove MO code to focus on the descriptive part
                project_desc = project_code.upper().replace(mo_code, '').strip('_')
                filename_upper = filename.upper()
                
                # Count matching characters in the descriptive part
                score = sum(1 for char in project_desc if char in filename_upper)
                
                print(f"[EXCEL_MATCH] Scoring '{filename}' against '{project_code}': score={score}")
                
                if score > best_score:
                    best_score = score
                    best_match = filepath
            
            if best_match:
                print(f"[EXCEL_MATCH] ✓ Best MO code match selected: '{os.path.basename(best_match)}'")
                return best_match
                        
    except Exception as e:
        print(f"[EXCEL_MATCH] Error finding Excel file: {e}")
        
    print(f"[EXCEL_MATCH] No matching Excel file found for project '{project_code}'")
    return None


def parse_excel_for_nesting(excel_path):
    """
    Parse Excel file for NESTING processing.
    Look in 1 PLATEN tab, Parcours column:
    - Rows starting with "N" = Nesting count
    - Rows starting with "Z" = Opdeelzaag count
    
    Returns:
        dict with item_count (total), nesting_count, opdeelzaag_count, mo_number, so_number, customer_name
        Note: nesting_count and opdeelzaag_count are kept for backward compatibility but item_count is the consolidated value
    """
    try:
        # Get correct sheet name
        sheet_name = get_sheet_name(excel_path)
        if not sheet_name:
            print(f"[NESTING] No valid sheet found in {excel_path}")
            return {
                'item_count': 0,
                'nesting_count': 0,
                'opdeelzaag_count': 0,
                'mo_number': None,
                'so_number': None,
                'customer_name': None,
                'color': None
            }
        
        # Find header row
        header_row = find_header_row(excel_path, sheet_name)
        
        # Read Excel file with correct header row
        df = pd.read_excel(excel_path, sheet_name=sheet_name, header=header_row)
        
        result = {
            'item_count': 0,
            'nesting_count': 0,
            'opdeelzaag_count': 0,
            'mo_number': None,
            'so_number': None,
            'customer_name': None,
            'color': None
        }
        
        # Extract MO/SO numbers and customer from filename or sheet
        filename = os.path.basename(excel_path)
        mo_match = re.search(r'(MO\d{4,5})', filename, re.IGNORECASE)
        if mo_match:
            result['mo_number'] = mo_match.group(1).upper()
        
        so_match = re.search(r'(S\d{5})', filename, re.IGNORECASE)
        if so_match:
            result['so_number'] = so_match.group(1).upper()
            
        # Try to extract customer name from filename (after last underscore before .xls)
        customer_match = re.search(r'_([^_]+)\.xls', filename)
        if customer_match:
            result['customer_name'] = customer_match.group(1)
        
        # Extract color from Excel
        result['color'] = extract_color_from_excel(excel_path, sheet_name)
        
        # Count Parcours entries
        if 'Parcours' in df.columns:
            parcours_col = df['Parcours'].astype(str).str.strip()
            
            # Count entries starting with 'N'
            result['nesting_count'] = parcours_col.str.startswith('N', na=False).sum()
            
            # Count entries starting with 'Z'
            result['opdeelzaag_count'] = parcours_col.str.startswith('Z', na=False).sum()
            
            # Calculate total item count (consolidated)
            result['item_count'] = result['nesting_count'] + result['opdeelzaag_count']
            
        return result
        
    except Exception as e:
        print(f"Error parsing Excel for NESTING: {e}")
        traceback.print_exc()
        return {
            'item_count': 0,
            'nesting_count': 0,
            'opdeelzaag_count': 0,
            'mo_number': None,
            'so_number': None,
            'customer_name': None,
            'color': None
        }


def parse_excel_for_accura(excel_path):
    """
    Parse Excel file for ACCURA processing.
    Look in 1 PLATEN tab at columns:
    - Afplak Boven
    - Afplak Onder  
    - Afplak Links
    - Afplak Rechts
    
    If any column has text = 1 item
    Count of non-empty cells = number of sides
    
    Returns:
        dict with item_count, aantal_sides (accura_sides), mo_number, so_number, customer_name, items_list
        Note: aantal_items is kept for backward compatibility but item_count is the consolidated value
    """
    try:
        # Get correct sheet name
        sheet_name = get_sheet_name(excel_path)
        if not sheet_name:
            print(f"[ACCURA] No valid sheet found in {excel_path}")
            return {
                'item_count': 0,
                'aantal_items': 0,  # Keep for backward compatibility
                'aantal_sides': 0,
                'mo_number': None,
                'so_number': None,
                'customer_name': None,
                'color': None,
                'items_list': []
            }
        
        # Find header row
        header_row = find_header_row(excel_path, sheet_name)
        
        # Read Excel file with correct header row
        df = pd.read_excel(excel_path, sheet_name=sheet_name, header=header_row)
        
        result = {
            'item_count': 0,
            'aantal_items': 0,  # Keep for backward compatibility
            'aantal_sides': 0,
            'mo_number': None,
            'so_number': None,
            'customer_name': None,
            'color': None,
            'items_list': []  # List of items for Excel generation
        }
        
        # Extract MO/SO numbers and customer
        filename = os.path.basename(excel_path)
        mo_match = re.search(r'(MO\d{4,5})', filename, re.IGNORECASE)
        if mo_match:
            result['mo_number'] = mo_match.group(1).upper()
        
        so_match = re.search(r'(S\d{5})', filename, re.IGNORECASE)
        if so_match:
            result['so_number'] = so_match.group(1).upper()
            
        customer_match = re.search(r'_([^_]+)\.xls', filename)
        if customer_match:
            result['customer_name'] = customer_match.group(1)
        
        # Extract color from Excel
        result['color'] = extract_color_from_excel(excel_path, sheet_name)
        
        # Define Afplak columns
        afplak_columns = ['Afplak Boven', 'Afplak Onder', 'Afplak Links', 'Afplak Rechts']
        
        # Check which columns exist
        existing_afplak_cols = [col for col in afplak_columns if col in df.columns]
        
        if existing_afplak_cols:
            # Process each row
            for idx, row in df.iterrows():
                sides_in_row = 0
                has_content = False
                
                # Count non-empty cells in Afplak columns
                for col in existing_afplak_cols:
                    value = str(row[col]).strip() if pd.notna(row[col]) else ''
                    if value and value.lower() not in ['nan', 'none', '']:
                        sides_in_row += 1
                        has_content = True
                
                # If any Afplak column has content, it's 1 item
                if has_content:
                    result['item_count'] += 1
                    result['aantal_items'] += 1  # Keep for backward compatibility
                    result['aantal_sides'] += sides_in_row
                    
                    # Extract Positie and Wand Naam for item list
                    positie = str(row.get('Positie', '')).strip() if pd.notna(row.get('Positie')) else ''
                    wand_naam = str(row.get('Wand Naam', '')).strip() if pd.notna(row.get('Wand Naam')) else ''
                    
                    # Format as "Positie - Wand Naam"
                    item_name = f"{positie} - {wand_naam}"
                    result['items_list'].append(item_name)
                    
        return result
        
    except Exception as e:
        print(f"Error parsing Excel for ACCURA: {e}")
        traceback.print_exc()
        return {
            'item_count': 0,
            'aantal_items': 0,  # Keep for backward compatibility
            'aantal_sides': 0,
            'mo_number': None,
            'so_number': None,
            'customer_name': None,
            'color': None,
            'items_list': []
        }


def parse_excel_for_boere(excel_path):
    """
    Parse Excel file for BOERE processing.
    Look in 1 PLATEN tab at Materiaal column.
    Every row with content in Materiaal = 1 count
    
    Returns:
        dict with item_count, mo_number, so_number, customer_name, items_list
    """
    try:
        # Get correct sheet name
        sheet_name = get_sheet_name(excel_path)
        if not sheet_name:
            print(f"[BOERE] No valid sheet found in {excel_path}")
            return {
                'item_count': 0,
                'mo_number': None,
                'so_number': None,
                'customer_name': None,
                'color': None,
                'items_list': []
            }
        
        # Find header row
        header_row = find_header_row(excel_path, sheet_name)
        
        # Read Excel file with correct header row
        df = pd.read_excel(excel_path, sheet_name=sheet_name, header=header_row)
        
        result = {
            'item_count': 0,
            'mo_number': None,
            'so_number': None,
            'customer_name': None,
            'color': None,
            'items_list': []  # List of items for Excel generation
        }
        
        # Extract MO/SO numbers and customer
        filename = os.path.basename(excel_path)
        mo_match = re.search(r'(MO\d{4,5})', filename, re.IGNORECASE)
        if mo_match:
            result['mo_number'] = mo_match.group(1).upper()
        
        so_match = re.search(r'(S\d{5})', filename, re.IGNORECASE)
        if so_match:
            result['so_number'] = so_match.group(1).upper()
            
        customer_match = re.search(r'_([^_]+)\.xls', filename)
        if customer_match:
            result['customer_name'] = customer_match.group(1)
        
        # Extract color from Excel
        result['color'] = extract_color_from_excel(excel_path, sheet_name)
        
        # Count Materiaal entries and collect items
        if 'Materiaal' in df.columns:
            for idx, row in df.iterrows():
                if pd.notna(row['Materiaal']):
                    result['item_count'] += 1
                    
                    # Extract Positie and Wand Naam for item list
                    positie = str(row.get('Positie', '')).strip() if pd.notna(row.get('Positie')) else ''
                    wand_naam = str(row.get('Wand Naam', '')).strip() if pd.notna(row.get('Wand Naam')) else ''
                    
                    # Format as "Positie - Wand Naam"
                    item_name = f"{positie} - {wand_naam}"
                    result['items_list'].append(item_name)
            
        return result
        
    except Exception as e:
        print(f"Error parsing Excel for BOERE: {e}")
        traceback.print_exc()
        return {
            'item_count': 0,
            'mo_number': None,
            'so_number': None,
            'customer_name': None,
            'color': None,
            'items_list': []
        }


def process_excel_for_all_types(excel_path, processor_types):
    """
    Process Excel file for multiple processor types at once.
    
    Args:
        excel_path: Path to Excel file
        processor_types: List of processing types needed
        
    Returns:
        dict with results for each processor type
    """
    results = {}
    
    try:
        # Get correct sheet name
        sheet_name = get_sheet_name(excel_path)
        if not sheet_name:
            print(f"[UNIFIED] No valid sheet found in {excel_path}")
            return results
        
        # Find header row
        header_row = find_header_row(excel_path, sheet_name)
        
        # Read Excel once with correct header row
        df = pd.read_excel(excel_path, sheet_name=sheet_name, header=header_row)
        
        # Extract common metadata
        filename = os.path.basename(excel_path)
        mo_number = None
        so_number = None
        customer_name = None
        color = None
        
        mo_match = re.search(r'(MO\d{4,5})', filename, re.IGNORECASE)
        if mo_match:
            mo_number = mo_match.group(1).upper()
        
        so_match = re.search(r'(S\d{5})', filename, re.IGNORECASE)
        if so_match:
            so_number = so_match.group(1).upper()
            
        customer_match = re.search(r'_([^_]+)\.xls', filename)
        if customer_match:
            customer_name = customer_match.group(1)
            
        # Extract color from Excel
        color = extract_color_from_excel(excel_path, sheet_name)
        
        # Process for each type
        for proc_type in processor_types:
            if proc_type == 'NESTING_PROCESSING':
                result = {
                    'item_count': 0,
                    'nesting_count': 0,
                    'opdeelzaag_count': 0,
                    'mo_number': mo_number,
                    'so_number': so_number,
                    'customer_name': customer_name,
                    'color': color
                }
                
                if 'Parcours' in df.columns:
                    parcours_col = df['Parcours'].astype(str).str.strip()
                    result['nesting_count'] = parcours_col.str.startswith('N', na=False).sum()
                    result['opdeelzaag_count'] = parcours_col.str.startswith('Z', na=False).sum()
                    # Calculate total item count (consolidated)
                    result['item_count'] = result['nesting_count'] + result['opdeelzaag_count']
                
                results[proc_type] = result
                
            elif proc_type == 'ACCURA_PROCESSING':
                result = {
                    'item_count': 0,
                    'aantal_items': 0,  # Keep for backward compatibility
                    'aantal_sides': 0,
                    'mo_number': mo_number,
                    'so_number': so_number,
                    'customer_name': customer_name,
                    'color': color,
                    'items_list': []  # Add items_list for Excel generation
                }
                
                afplak_columns = ['Afplak Boven', 'Afplak Onder', 'Afplak Links', 'Afplak Rechts']
                existing_afplak_cols = [col for col in afplak_columns if col in df.columns]
                
                if existing_afplak_cols:
                    for idx, row in df.iterrows():
                        sides_in_row = 0
                        has_content = False
                        
                        for col in existing_afplak_cols:
                            value = str(row[col]).strip() if pd.notna(row[col]) else ''
                            if value and value.lower() not in ['nan', 'none', '']:
                                sides_in_row += 1
                                has_content = True
                        
                        if has_content:
                            result['item_count'] += 1
                            result['aantal_items'] += 1  # Keep for backward compatibility
                            result['aantal_sides'] += sides_in_row
                            
                            # Extract Positie and Wand Naam for item list
                            positie = str(row.get('Positie', '')).strip() if pd.notna(row.get('Positie')) else ''
                            wand_naam = str(row.get('Wand Naam', '')).strip() if pd.notna(row.get('Wand Naam')) else ''
                            
                            # Format as "Positie - Wand Naam"
                            item_name = f"{positie} - {wand_naam}"
                            result['items_list'].append(item_name)
                
                results[proc_type] = result
                
            elif proc_type == 'BOERE_PROCESSING':
                result = {
                    'item_count': 0,
                    'mo_number': mo_number,
                    'so_number': so_number,
                    'customer_name': customer_name,
                    'color': color,
                    'items_list': []  # Add items_list for Excel generation
                }
                
                if 'Materiaal' in df.columns:
                    for idx, row in df.iterrows():
                        if pd.notna(row['Materiaal']):
                            result['item_count'] += 1
                            
                            # Extract Positie and Wand Naam for item list
                            positie = str(row.get('Positie', '')).strip() if pd.notna(row.get('Positie')) else ''
                            wand_naam = str(row.get('Wand Naam', '')).strip() if pd.notna(row.get('Wand Naam')) else ''
                            
                            # Format as "Positie - Wand Naam"
                            item_name = f"{positie} - {wand_naam}"
                            result['items_list'].append(item_name)
                
                results[proc_type] = result
                
            elif proc_type == 'MASSIEF_PROCESSING':
                result = {
                    'item_count': 0,
                    'mo_number': mo_number,
                    'so_number': so_number,
                    'customer_name': customer_name,
                    'color': color,
                    'items_list': []
                }
                
                if 'Materiaal' in df.columns:
                    for idx, row in df.iterrows():
                        materiaal_value = str(row['Materiaal']) if pd.notna(row['Materiaal']) else ''
                        # Check if row contains "Massief_" (case-insensitive)
                        if 'massief_' in materiaal_value.lower():
                            result['item_count'] += 1
                            
                            # Use Wand Naam for item list (not Positie - Wand Naam format)
                            wand_naam = str(row.get('Wand Naam', '')).strip() if pd.notna(row.get('Wand Naam')) else ''
                            
                            # Add Wand Naam directly as the item
                            if wand_naam:
                                result['items_list'].append(wand_naam)
                            else:
                                # Fallback to material name if no Wand Naam
                                result['items_list'].append(materiaal_value)
                
                results[proc_type] = result
                
            elif proc_type == 'HANDWERK_PROCESSING':
                result = {
                    'item_count': 0,
                    'mo_number': mo_number,
                    'so_number': so_number,
                    'customer_name': customer_name,
                    'color': color,
                    'items_list': []
                }
                
                if 'Commentaar' in df.columns:
                    for idx, row in df.iterrows():
                        commentaar_value = str(row['Commentaar']) if pd.notna(row['Commentaar']) else ''
                        # Check if row contains "(HAND)" (case-insensitive)
                        if '(hand)' in commentaar_value.lower():
                            result['item_count'] += 1
                            
                            # Use Wand Naam for item list
                            wand_naam = str(row.get('Wand Naam', '')).strip() if pd.notna(row.get('Wand Naam')) else ''
                            
                            # Add Wand Naam directly as the item
                            if wand_naam:
                                result['items_list'].append(wand_naam)
                            else:
                                # Fallback to row description if no Wand Naam
                                result['items_list'].append(f"HAND item {result['item_count']}")
                
                results[proc_type] = result
                
    except Exception as e:
        print(f"Error processing Excel for multiple types: {e}")
        traceback.print_exc()
        
    return results


def generate_excel_for_accura(items_list, mo_number, so_number, customer_name, project_name=None):
    """
    Generate Excel file for ACCURA processing with item list.
    
    Args:
        items_list: List of items formatted as "Positie - Wand Naam"
        mo_number: MO number for filename
        so_number: SO number for filename
        customer_name: Customer name for filename
        project_name: Optional project name from BarcodeMaster
    
    Returns:
        Path to generated Excel file or None if failed
    """
    try:
        # Get output directory from DATABASE
        import requests
        import json
        
        # Load from database API - use config to get correct API URL
        from config_utils import get_config
        config = get_config()
        api_url = config.get('api_url', 'http://localhost:5000').rstrip('/')
        # Remove /log suffix if present to get base URL
        base_url = api_url.replace('/log', '') if api_url.endswith('/log') else api_url
        
        response = requests.get(f'{base_url}/api/settings', timeout=5)
        if response.status_code != 200:
            raise Exception(f"Failed to load settings from database API: HTTP {response.status_code}")
        
        data = response.json()
        if not data.get('success'):
            raise Exception(f"Database API returned error: {data.get('error', 'Unknown error')}")
        
        settings = data.get('settings', {})
        output_dir = settings.get('accura_output_dir')
        if not output_dir:
            raise Exception("accura_output_dir not configured in database settings")
        
        # Normalize path
        output_dir = os.path.normpath(output_dir)
        os.makedirs(output_dir, exist_ok=True)
        
        # Use project name if provided to ensure consistency
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if project_name:
            # Use the actual project name to prevent duplicate project issues
            filename = f"{project_name}_{timestamp}.xlsx"
        else:
            # Fallback: use only MO number to avoid confusion
            filename = f"{mo_number}_{timestamp}.xlsx"
        output_path = os.path.join(output_dir, filename)
        
        # Create DataFrame with Item and Status columns
        df = pd.DataFrame({
            'Item': items_list,
            'Status': [''] * len(items_list)  # Empty status column
        })
        
        # Save to Excel with metadata if project_name provided
        if project_name:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Main data sheet
                df.to_excel(writer, sheet_name='Items', index=False)
                
                # Add metadata sheet
                metadata_df = pd.DataFrame({
                    'Property': ['project_name', 'mo_number', 'so_number', 'customer_name', 'created_by'],
                    'Value': [project_name, mo_number, so_number, customer_name, 'BarcodeMaster']
                })
                metadata_df.to_excel(writer, sheet_name='_ProjectInfo', index=False)
                
                # Hide the metadata sheet
                workbook = writer.book
                worksheet = workbook['_ProjectInfo']
                worksheet.sheet_state = 'hidden'
        else:
            # Fallback to simple Excel write
            df.to_excel(output_path, index=False, sheet_name='Items')
        
        print(f"[ACCURA] Excel file generated: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"Error generating Excel for ACCURA: {e}")
        traceback.print_exc()
        return None


def generate_excel_for_boere(items_list, mo_number, so_number, customer_name, project_name=None):
    """
    Generate Excel file for BOERE processing with item list.
    
    Args:
        items_list: List of items formatted as "Positie - Wand Naam"
        mo_number: MO number for filename
        so_number: SO number for filename
        customer_name: Customer name for filename
        project_name: Optional project name from BarcodeMaster
    
    Returns:
        Path to generated Excel file or None if failed
    """
    try:
        # Get output directory from DATABASE
        import requests
        import json
        
        # Load from database API - use config to get correct API URL
        from config_utils import get_config
        config = get_config()
        api_url = config.get('api_url', 'http://localhost:5000').rstrip('/')
        # Remove /log suffix if present to get base URL
        base_url = api_url.replace('/log', '') if api_url.endswith('/log') else api_url
        
        response = requests.get(f'{base_url}/api/settings', timeout=5)
        if response.status_code != 200:
            raise Exception(f"Failed to load settings from database API: HTTP {response.status_code}")
        
        data = response.json()
        if not data.get('success'):
            raise Exception(f"Database API returned error: {data.get('error', 'Unknown error')}")
        
        settings = data.get('settings', {})
        output_dir = settings.get('boere_output_dir')
        if not output_dir:
            raise Exception("boere_output_dir not configured in database settings")
        
        # Normalize path
        output_dir = os.path.normpath(output_dir)
        os.makedirs(output_dir, exist_ok=True)
        
        # Use project name if provided to ensure consistency
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if project_name:
            # Use the actual project name to prevent duplicate project issues
            filename = f"{project_name}_{timestamp}.xlsx"
        else:
            # Fallback: use only MO number to avoid confusion
            filename = f"{mo_number}_{timestamp}.xlsx"
        output_path = os.path.join(output_dir, filename)
        
        # Create DataFrame with Item and Status columns
        df = pd.DataFrame({
            'Item': items_list,
            'Status': [''] * len(items_list)  # Empty status column
        })
        
        # Save to Excel with metadata if project_name provided
        if project_name:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Main data sheet
                df.to_excel(writer, sheet_name='Items', index=False)
                
                # Add metadata sheet
                metadata_df = pd.DataFrame({
                    'Property': ['project_name', 'mo_number', 'so_number', 'customer_name', 'created_by'],
                    'Value': [project_name, mo_number, so_number, customer_name, 'BarcodeMaster']
                })
                metadata_df.to_excel(writer, sheet_name='_ProjectInfo', index=False)
                
                # Hide the metadata sheet
                workbook = writer.book
                worksheet = workbook['_ProjectInfo']
                worksheet.sheet_state = 'hidden'
        else:
            # Fallback to simple Excel write
            df.to_excel(output_path, index=False, sheet_name='Items')
        
        print(f"[BOERE] Excel file generated: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"Error generating Excel for BOERE: {e}")
        traceback.print_exc()
        return None


def parse_excel_for_massief(excel_path):
    """
    Parse Excel file for MASSIEF processing.
    Look in 1 PLATEN tab at Materiaal column.
    Every row with "Massief_" in Materiaal = 1 count
    Use "Wand Naam" column for item list
    
    Returns:
        dict with item_count, mo_number, so_number, customer_name, items_list
    """
    try:
        # Get correct sheet name
        sheet_name = get_sheet_name(excel_path)
        if not sheet_name:
            print(f"[MASSIEF] No valid sheet found in {excel_path}")
            return {
                'item_count': 0,
                'mo_number': None,
                'so_number': None,
                'customer_name': None,
                'color': None,
                'items_list': []
            }
        
        # Find header row
        header_row = find_header_row(excel_path, sheet_name)
        
        # Read Excel file with correct header row
        df = pd.read_excel(excel_path, sheet_name=sheet_name, header=header_row)
        
        result = {
            'item_count': 0,
            'mo_number': None,
            'so_number': None,
            'customer_name': None,
            'color': None,
            'items_list': []  # List of items for Excel generation
        }
        
        # Extract MO/SO numbers and customer
        filename = os.path.basename(excel_path)
        mo_match = re.search(r'(MO\d{4,5})', filename, re.IGNORECASE)
        if mo_match:
            result['mo_number'] = mo_match.group(1).upper()
        
        so_match = re.search(r'(S\d{5})', filename, re.IGNORECASE)
        if so_match:
            result['so_number'] = so_match.group(1).upper()
            
        customer_match = re.search(r'_([^_]+)\.xls', filename)
        if customer_match:
            result['customer_name'] = customer_match.group(1)
        
        # Extract color from Excel
        result['color'] = extract_color_from_excel(excel_path, sheet_name)
        
        # Count Massief entries and collect items
        if 'Materiaal' in df.columns:
            for idx, row in df.iterrows():
                materiaal_value = str(row['Materiaal']) if pd.notna(row['Materiaal']) else ''
                # Check if row contains "Massief_" (case-insensitive)
                if 'massief_' in materiaal_value.lower():
                    result['item_count'] += 1
                    
                    # Use Wand Naam for item list (not Positie - Wand Naam format)
                    wand_naam = str(row.get('Wand Naam', '')).strip() if pd.notna(row.get('Wand Naam')) else ''
                    
                    # Add Wand Naam directly as the item
                    if wand_naam:
                        result['items_list'].append(wand_naam)
                    else:
                        # Fallback to material name if no Wand Naam
                        result['items_list'].append(materiaal_value)
            
        return result
        
    except Exception as e:
        print(f"Error parsing Excel for MASSIEF: {e}")
        traceback.print_exc()
        return {
            'item_count': 0,
            'mo_number': None,
            'so_number': None,
            'customer_name': None,
            'color': None,
            'items_list': []
        }


def generate_excel_for_massief(items_list, mo_number, so_number, customer_name, project_name=None):
    """
    Generate Excel file for MASSIEF processing with item list.
    
    Args:
        items_list: List of items (Wand Naam values)
        mo_number: MO number for filename
        so_number: SO number for filename
        customer_name: Customer name for filename
        project_name: Optional project name from BarcodeMaster
    
    Returns:
        Path to generated Excel file or None if failed
    """
    try:
        # Get output directory from DATABASE
        import requests
        import json
        
        # Load from database API - use config to get correct API URL
        from config_utils import get_config
        config = get_config()
        api_url = config.get('api_url', 'http://localhost:5000').rstrip('/')
        # Remove /log suffix if present to get base URL
        base_url = api_url.replace('/log', '') if api_url.endswith('/log') else api_url
        
        response = requests.get(f'{base_url}/api/settings', timeout=5)
        if response.status_code != 200:
            raise Exception(f"Failed to load settings from database API: HTTP {response.status_code}")
        
        data = response.json()
        if not data.get('success'):
            raise Exception(f"Database API returned error: {data.get('error', 'Unknown error')}")
        
        settings = data.get('settings', {})
        output_dir = settings.get('massief_output_dir')
        if not output_dir:
            raise Exception("massief_output_dir not configured in database settings")
        
        # Normalize path
        output_dir = os.path.normpath(output_dir)
        os.makedirs(output_dir, exist_ok=True)
        
        # Use project name if provided to ensure consistency
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if project_name:
            # Use the actual project name to prevent duplicate project issues
            filename = f"{project_name}_{timestamp}.xlsx"
        else:
            # Fallback: use only MO number to avoid confusion
            filename = f"{mo_number}_{timestamp}.xlsx"
        output_path = os.path.join(output_dir, filename)
        
        # Create DataFrame with Item and Status columns
        df = pd.DataFrame({
            'Item': items_list,
            'Status': [''] * len(items_list)  # Empty status column
        })
        
        # Save to Excel with metadata if project_name provided
        if project_name:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Main data sheet
                df.to_excel(writer, sheet_name='Items', index=False)
                
                # Add metadata sheet
                metadata_df = pd.DataFrame({
                    'Property': ['project_name', 'mo_number', 'so_number', 'customer_name', 'created_by'],
                    'Value': [project_name, mo_number, so_number, customer_name, 'BarcodeMaster']
                })
                metadata_df.to_excel(writer, sheet_name='_ProjectInfo', index=False)
                
                # Hide the metadata sheet
                workbook = writer.book
                worksheet = workbook['_ProjectInfo']
                worksheet.sheet_state = 'hidden'
        else:
            # Fallback to simple Excel write
            df.to_excel(output_path, index=False, sheet_name='Items')
        
        print(f"[MASSIEF] Excel file generated: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"Error generating Excel for MASSIEF: {e}")
        traceback.print_exc()
        return None


def parse_excel_for_handwerk(excel_path):
    """
    Parse Excel file for HANDWERK processing.
    Look in 1 PLATEN tab at Commentaar column.
    Every row with "(HAND)" in Commentaar = 1 count
    Use "Wand Naam" column for item list
    
    Returns:
        dict with item_count, mo_number, so_number, customer_name, items_list
    """
    try:
        # Get correct sheet name
        sheet_name = get_sheet_name(excel_path)
        if not sheet_name:
            print(f"[HANDWERK] No valid sheet found in {excel_path}")
            return {
                'item_count': 0,
                'mo_number': None,
                'so_number': None,
                'customer_name': None,
                'color': None,
                'items_list': []
            }
        
        # Find header row
        header_row = find_header_row(excel_path, sheet_name)
        
        # Read Excel file with correct header row
        df = pd.read_excel(excel_path, sheet_name=sheet_name, header=header_row)
        
        result = {
            'item_count': 0,
            'mo_number': None,
            'so_number': None,
            'customer_name': None,
            'color': None,
            'items_list': []  # List of items for Excel generation
        }
        
        # Extract MO/SO numbers and customer
        filename = os.path.basename(excel_path)
        mo_match = re.search(r'(MO\d{4,5})', filename, re.IGNORECASE)
        if mo_match:
            result['mo_number'] = mo_match.group(1).upper()
        
        so_match = re.search(r'(S\d{5})', filename, re.IGNORECASE)
        if so_match:
            result['so_number'] = so_match.group(1).upper()
            
        customer_match = re.search(r'_([^_]+)\.xls', filename)
        if customer_match:
            result['customer_name'] = customer_match.group(1)
        
        # Extract color from Excel
        result['color'] = extract_color_from_excel(excel_path, sheet_name)
        
        # Count (HAND) entries and collect items
        if 'Commentaar' in df.columns:
            for idx, row in df.iterrows():
                commentaar_value = str(row['Commentaar']) if pd.notna(row['Commentaar']) else ''
                # Check if row contains "(HAND)" (case-insensitive)
                if '(hand)' in commentaar_value.lower():
                    result['item_count'] += 1
                    
                    # Use Wand Naam for item list
                    wand_naam = str(row.get('Wand Naam', '')).strip() if pd.notna(row.get('Wand Naam')) else ''
                    
                    # Add Wand Naam directly as the item
                    if wand_naam:
                        result['items_list'].append(wand_naam)
                    else:
                        # Fallback to row description if no Wand Naam
                        result['items_list'].append(f"HAND item {result['item_count']}")
            
        return result
        
    except Exception as e:
        print(f"Error parsing Excel for HANDWERK: {e}")
        traceback.print_exc()
        return {
            'item_count': 0,
            'mo_number': None,
            'so_number': None,
            'customer_name': None,
            'color': None,
            'items_list': []
        }


def generate_excel_for_handwerk(items_list, mo_number, so_number, customer_name, project_name=None):
    """
    Generate Excel file for HANDWERK processing with item list.
    
    Args:
        items_list: List of items (Wand Naam values)
        mo_number: MO number for filename
        so_number: SO number for filename
        customer_name: Customer name for filename
        project_name: Optional project name from BarcodeMaster
    
    Returns:
        Path to generated Excel file or None if failed
    """
    try:
        # Get output directory from DATABASE
        import requests
        import json
        
        # Load from database API - use config to get correct API URL
        from config_utils import get_config
        config = get_config()
        api_url = config.get('api_url', 'http://localhost:5000').rstrip('/')
        # Remove /log suffix if present to get base URL
        base_url = api_url.replace('/log', '') if api_url.endswith('/log') else api_url
        
        response = requests.get(f'{base_url}/api/settings', timeout=5)
        if response.status_code != 200:
            raise Exception(f"Failed to load settings from database API: HTTP {response.status_code}")
        
        data = response.json()
        if not data.get('success'):
            raise Exception(f"Database API returned error: {data.get('error', 'Unknown error')}")
        
        settings = data.get('settings', {})
        output_dir = settings.get('handwerk_output_dir')
        if not output_dir:
            raise Exception("handwerk_output_dir not configured in database settings")
        
        # Normalize path
        output_dir = os.path.normpath(output_dir)
        os.makedirs(output_dir, exist_ok=True)
        
        # Use project name if provided to ensure consistency
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if project_name:
            # Use the actual project name to prevent duplicate project issues
            filename = f"{project_name}_{timestamp}.xlsx"
        else:
            # Fallback: use only MO number to avoid confusion
            filename = f"{mo_number}_{timestamp}.xlsx"
        output_path = os.path.join(output_dir, filename)
        
        # Create DataFrame with Item and Status columns
        df = pd.DataFrame({
            'Item': items_list,
            'Status': [''] * len(items_list)  # Empty status column
        })
        
        # Save to Excel with metadata if project_name provided
        if project_name:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Main data sheet
                df.to_excel(writer, sheet_name='Items', index=False)
                
                # Add metadata sheet
                metadata_df = pd.DataFrame({
                    'Property': ['project_name', 'mo_number', 'so_number', 'customer_name', 'created_by'],
                    'Value': [project_name, mo_number, so_number, customer_name, 'BarcodeMaster']
                })
                metadata_df.to_excel(writer, sheet_name='_ProjectInfo', index=False)
                
                # Hide the metadata sheet
                workbook = writer.book
                worksheet = workbook['_ProjectInfo']
                worksheet.sheet_state = 'hidden'
        else:
            # Fallback to simple Excel write
            df.to_excel(output_path, index=False, sheet_name='Items')
        
        print(f"[HANDWERK] Excel file generated: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"Error generating Excel for HANDWERK: {e}")
        traceback.print_exc()
        return None


def generate_hops_for_manual_entry(items_list, mo_number, so_number, customer_name, project_name=None):
    """
    Generate HOPS directory structure and Excel file for manual entry.
    Creates a directory in the OPUS/KORPUS path and generates an Excel file with generic items.

    Args:
        items_list: List of item names/descriptions
        mo_number: MO number (e.g., 'MO6798')
        so_number: SO number (e.g., 'S03673')
        customer_name: Customer name
        project_name: Full project name (e.g., 'MO6798_Vestiaire_(16-16)')

    Returns:
        Path to the generated Excel file, or None if failed
    """
    try:
        print(f"[HOPS_GEN DEBUG] Received parameters:")
        print(f"[HOPS_GEN DEBUG]   project_name: '{project_name}'")
        print(f"[HOPS_GEN DEBUG]   mo_number: '{mo_number}' (type: {type(mo_number)})")
        print(f"[HOPS_GEN DEBUG]   so_number: '{so_number}'")
        print(f"[HOPS_GEN DEBUG]   customer_name: '{customer_name}'")
        import pandas as pd
        from datetime import datetime
        import requests
        
        # Load OPUS path from database API
        from config_utils import get_config
        config = get_config()
        api_url = config.get('api_url', 'http://localhost:5000').rstrip('/')
        base_url = api_url.replace('/log', '') if api_url.endswith('/log') else api_url
        
        response = requests.get(f'{base_url}/api/settings', timeout=5)
        if response.status_code != 200:
            raise Exception(f"Failed to load settings from database API: HTTP {response.status_code}")
        
        data = response.json()
        if not data.get('success'):
            raise Exception(f"Database API returned error: {data.get('error', 'Unknown error')}")
        
        settings = data.get('settings', {})

        # Get OPUS path from user paths (correct database key)
        user_paths = settings.get('scanner_panel_open_event_user_paths', {})
        opus_path = user_paths.get('OPUS')

        if not opus_path:
            raise Exception("OPUS path not configured in database settings (User Configuration tab)")
        
        # Normalize path
        opus_path = os.path.normpath(opus_path)
        
        # Create project directory name
        # Format: Just the project_code from manual entry (no timestamp)
        if project_name:
            # Use project name as-is
            dir_name = project_name
        else:
            # Fallback: create name from MO number
            dir_name = f"{mo_number}_Manual"
        
        # Create full directory path
        project_dir = os.path.join(opus_path, dir_name)
        os.makedirs(project_dir, exist_ok=True)
        
        # Create Excel file in the project directory
        excel_filename = f"{dir_name}.xlsx"
        excel_path = os.path.join(project_dir, excel_filename)
        
        # Create DataFrame with Item and Status columns
        df = pd.DataFrame({
            'Item': items_list,
            'Status': [''] * len(items_list)
        })
        
        # Save to Excel with metadata
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            # Main data sheet
            df.to_excel(writer, sheet_name='Items', index=False)
            
            # Add metadata sheet
            print(f"[HOPS_GEN DEBUG] Writing metadata with mo_number: '{mo_number}' (type: {type(mo_number)})")
            metadata_df = pd.DataFrame({
                'Property': ['project_name', 'mo_number', 'so_number', 'customer_name', 'created_by', 'directory'],
                'Value': [project_name or dir_name, mo_number, so_number, customer_name, 'BarcodeMaster', project_dir]
            })
            print(f"[HOPS_GEN DEBUG] Metadata DataFrame created:")
            print(metadata_df)
            metadata_df.to_excel(writer, sheet_name='_ProjectInfo', index=False)
            
            # Hide the metadata sheet
            workbook = writer.book
            worksheet = workbook['_ProjectInfo']
            worksheet.sheet_state = 'hidden'
        
        print(f"[HOPS] Excel file and directory created: {excel_path}")
        return excel_path
        
    except Exception as e:
        print(f"Error generating HOPS for manual entry: {e}")
        traceback.print_exc()
        return None


def generate_mdb_for_manual_entry(items_list, mo_number, so_number, customer_name, project_name=None):
    """
    Generate MDB Excel file for manual entry.
    Creates an Excel file in the KL GANNOMAT path with generic items.
    Note: Actual MDB file creation requires Access/ODBC, so we create Excel as placeholder.
    
    Args:
        items_list: List of item names/descriptions (ProgramNumbers)
        mo_number: MO number (e.g., 'MO6798')
        so_number: SO number (e.g., 'S03673')
        customer_name: Customer name
        project_name: Full project name (e.g., 'MO6798_Vestiaire_(16-16)')
    
    Returns:
        Path to the generated Excel file, or None if failed
    """
    try:
        import pandas as pd
        from datetime import datetime
        import requests
        
        # Load KL GANNOMAT path from database API
        from config_utils import get_config
        config = get_config()
        api_url = config.get('api_url', 'http://localhost:5000').rstrip('/')
        base_url = api_url.replace('/log', '') if api_url.endswith('/log') else api_url
        
        response = requests.get(f'{base_url}/api/settings', timeout=5)
        if response.status_code != 200:
            raise Exception(f"Failed to load settings from database API: HTTP {response.status_code}")
        
        data = response.json()
        if not data.get('success'):
            raise Exception(f"Database API returned error: {data.get('error', 'Unknown error')}")
        
        settings = data.get('settings', {})

        # Get KL GANNOMAT path from user paths (correct database key)
        user_paths = settings.get('scanner_panel_open_event_user_paths', {})
        mdb_path = user_paths.get('KL GANNOMAT')

        if not mdb_path:
            raise Exception("KL GANNOMAT path not configured in database settings (User Configuration tab)")
        
        # Normalize path
        mdb_path = os.path.normpath(mdb_path)
        os.makedirs(mdb_path, exist_ok=True)
        
        # Create filename
        # Format: Just the project_code from manual entry (no timestamp)
        if project_name:
            # Use project name as-is
            filename = f"{project_name}.xlsx"
        else:
            # Fallback: create name from MO number
            filename = f"{mo_number}_Manual.xlsx"
        
        excel_path = os.path.join(mdb_path, filename)
        
        # Create DataFrame with Item and Status columns (matching MDB format)
        df = pd.DataFrame({
            'Item': items_list,
            'Status': [''] * len(items_list)
        })
        
        # Save to Excel with metadata
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            # Main data sheet
            df.to_excel(writer, sheet_name='Items', index=False)
            
            # Add metadata sheet
            metadata_df = pd.DataFrame({
                'Property': ['project_name', 'mo_number', 'so_number', 'customer_name', 'created_by', 'type'],
                'Value': [project_name or filename.replace('.xlsx', ''), mo_number, so_number, customer_name, 'BarcodeMaster', 'MDB_MANUAL']
            })
            metadata_df.to_excel(writer, sheet_name='_ProjectInfo', index=False)
            
            # Hide the metadata sheet
            workbook = writer.book
            worksheet = workbook['_ProjectInfo']
            worksheet.sheet_state = 'hidden'
        
        print(f"[MDB] Excel file created: {excel_path}")
        return excel_path
        
    except Exception as e:
        print(f"Error generating MDB Excel for manual entry: {e}")
        traceback.print_exc()
        return None