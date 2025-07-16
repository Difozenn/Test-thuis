
def get_accura_count_fixed(lines):
    """Count rows with actual L1/L2/B1/B2 data values"""
    
    accura_count = 0
    in_accura_table = False
    
    for i, line in enumerate(lines):
        line_clean = line.strip()
        
        # Detect L1/L2/B1/B2 table header
        if 'L1' in line and 'L2' in line and 'B1' in line and 'B2' in line:
            in_accura_table = True
            continue
        
        if in_accura_table:
            # Count numbered rows with enough numeric values
            if re.match(r'^\d+\s+', line_clean):
                parts = line_clean.split()
                # Must have item number + name + 4 dimensions (L1,L2,B1,B2)
                numeric_values = [p for p in parts if re.match(r'^\d+(\.\d+)?$', p)]
                if len(numeric_values) >= 5:  # 1 for item number + 4 for dimensions
                    accura_count += 1
            
            # End of table
            elif line_clean == '' or 'Aantal onderdelen' in line:
                in_accura_table = False
    
    return accura_count
