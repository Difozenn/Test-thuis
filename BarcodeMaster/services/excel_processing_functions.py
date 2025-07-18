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
        
        # Extract just the MO code if present
        mo_match = re.search(r'(MO\d{5})', project_code, re.IGNORECASE)
        mo_code = mo_match.group(1).upper() if mo_match else project_code.upper()
        
        print(f"[EXCEL_MATCH] Extracted MO code: '{mo_code}'")
        
        # Search for Excel files in directory
        for filename in os.listdir(directory):
            if filename.endswith(('.xlsx', '.xls')):
                print(f"[EXCEL_MATCH] Checking file: '{filename}'")
                
                # Check if MO code is in filename
                if mo_code in filename.upper():
                    print(f"[EXCEL_MATCH] MO code '{mo_code}' found in filename")
                    
                    # Additional check: see if the full project code pattern matches
                    if project_code.upper() in filename.upper():
                        print(f"[EXCEL_MATCH] ✓ Full project code '{project_code}' matches filename '{filename}'")
                        return os.path.join(directory, filename)
                    # Fallback to just MO code match
                    else:
                        print(f"[EXCEL_MATCH] ✓ MO code match fallback for '{filename}'")
                        return os.path.join(directory, filename)
                else:
                    print(f"[EXCEL_MATCH] MO code '{mo_code}' not found in '{filename}'")
                        
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
        mo_match = re.search(r'(MO\d{5})', filename, re.IGNORECASE)
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
        mo_match = re.search(r'(MO\d{5})', filename, re.IGNORECASE)
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
        mo_match = re.search(r'(MO\d{5})', filename, re.IGNORECASE)
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
        
        mo_match = re.search(r'(MO\d{5})', filename, re.IGNORECASE)
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
                
    except Exception as e:
        print(f"Error processing Excel for multiple types: {e}")
        traceback.print_exc()
        
    return results


def generate_excel_for_accura(items_list, mo_number, so_number, customer_name):
    """
    Generate Excel file for ACCURA processing with item list.
    
    Args:
        items_list: List of items formatted as "Positie - Wand Naam"
        mo_number: MO number for filename
        so_number: SO number for filename
        customer_name: Customer name for filename
    
    Returns:
        Path to generated Excel file or None if failed
    """
    try:
        # Create directory if it doesn't exist - use system-appropriate path
        if os.name == 'nt':  # Windows
            output_dir = "C:/ACCURA"
        else:  # Linux/Unix
            output_dir = "/tmp/ACCURA"
        os.makedirs(output_dir, exist_ok=True)
        
        # Create filename similar to HOPS/MDB pattern
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{mo_number}_{so_number}_{customer_name}_{timestamp}.xlsx"
        output_path = os.path.join(output_dir, filename)
        
        # Create DataFrame with Item and Status columns
        df = pd.DataFrame({
            'Item': items_list,
            'Status': [''] * len(items_list)  # Empty status column
        })
        
        # Save to Excel
        df.to_excel(output_path, index=False, sheet_name='Items')
        
        print(f"[ACCURA] Excel file generated: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"Error generating Excel for ACCURA: {e}")
        traceback.print_exc()
        return None


def generate_excel_for_boere(items_list, mo_number, so_number, customer_name):
    """
    Generate Excel file for BOERE processing with item list.
    
    Args:
        items_list: List of items formatted as "Positie - Wand Naam"
        mo_number: MO number for filename
        so_number: SO number for filename
        customer_name: Customer name for filename
    
    Returns:
        Path to generated Excel file or None if failed
    """
    try:
        # Create directory if it doesn't exist - use system-appropriate path
        if os.name == 'nt':  # Windows
            output_dir = "C:/BOERE"
        else:  # Linux/Unix
            output_dir = "/tmp/BOERE"
        os.makedirs(output_dir, exist_ok=True)
        
        # Create filename similar to HOPS/MDB pattern
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{mo_number}_{so_number}_{customer_name}_{timestamp}.xlsx"
        output_path = os.path.join(output_dir, filename)
        
        # Create DataFrame with Item and Status columns
        df = pd.DataFrame({
            'Item': items_list,
            'Status': [''] * len(items_list)  # Empty status column
        })
        
        # Save to Excel
        df.to_excel(output_path, index=False, sheet_name='Items')
        
        print(f"[BOERE] Excel file generated: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"Error generating Excel for BOERE: {e}")
        traceback.print_exc()
        return None