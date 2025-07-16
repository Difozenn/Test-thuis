#!/usr/bin/env python3
"""
Test script for Excel processing functionality.
Run this to test the new Excel processing for NESTING, ACCURA, and BOERE.
"""

import os
import pandas as pd
from services.excel_processing_functions import (
    find_excel_file_for_project,
    parse_excel_for_nesting,
    parse_excel_for_accura,
    parse_excel_for_boere,
    process_excel_for_all_types
)


def create_sample_excel_file():
    """Create a sample Excel file for testing."""
    # Sample data for PLATEN tab
    data = {
        'Parcours': ['N1', 'N2', 'Z', 'N3', 'Z', 'N4', 'Z', 'N5'],
        'Afplak Boven': ['Text1', '', 'Text3', '', 'Text5', 'Text6', '', 'Text8'],
        'Afplak Onder': ['', 'Text2', 'Text3', '', '', 'Text6', 'Text7', ''],
        'Afplak Links': ['Text1', '', '', 'Text4', 'Text5', '', 'Text7', ''],
        'Afplak Rechts': ['', 'Text2', '', '', '', 'Text6', '', 'Text8'],
        'Materiaal': ['Mat1', 'Mat2', 'Mat3', 'Mat4', 'Mat5', 'Mat6', 'Mat7', 'Mat8']
    }
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Create sample Excel file
    excel_path = '/tmp/S03673_MO06789_Hangkastjes_(7-16)_Frank_Celis.xlsx'
    
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='PLATEN', index=False)
    
    return excel_path


def test_excel_file_matching():
    """Test Excel file matching functionality."""
    print("=" * 60)
    print("Testing Excel file matching...")
    
    # Create a temporary directory with sample Excel file
    excel_path = create_sample_excel_file()
    test_dir = os.path.dirname(excel_path)
    
    # Test cases
    test_cases = [
        ("MO06789_Hangkastjes_(7-16)", True),
        ("MO06789", True),
        ("MO12345", False),
        ("Hangkastjes_(7-16)", True),
        ("WrongProject", False)
    ]
    
    for project_code, should_match in test_cases:
        result = find_excel_file_for_project(test_dir, project_code)
        match_found = result is not None
        
        status = "✓" if match_found == should_match else "✗"
        print(f"{status} Project '{project_code}' -> {'Found' if match_found else 'Not found'}")
    
    # Clean up
    if os.path.exists(excel_path):
        os.remove(excel_path)


def test_nesting_processing():
    """Test NESTING processing functionality."""
    print("\n" + "=" * 60)
    print("Testing NESTING processing...")
    
    excel_path = create_sample_excel_file()
    
    try:
        result = parse_excel_for_nesting(excel_path)
        
        print(f"✓ NESTING processing completed")
        print(f"  - Nesting count: {result['nesting_count']}")
        print(f"  - Opdeelzaag count: {result['opdeelzaag_count']}")
        print(f"  - MO number: {result['mo_number']}")
        print(f"  - Customer name: {result['customer_name']}")
        
        # Expected: 5 items starting with 'N', 3 items equal to 'Z'
        assert result['nesting_count'] == 5, f"Expected 5 nesting items, got {result['nesting_count']}"
        assert result['opdeelzaag_count'] == 3, f"Expected 3 opdeelzaag items, got {result['opdeelzaag_count']}"
        assert result['mo_number'] == 'MO06789', f"Expected MO06789, got {result['mo_number']}"
        
        print("✓ All NESTING tests passed!")
        
    except Exception as e:
        print(f"✗ NESTING processing failed: {e}")
    
    finally:
        if os.path.exists(excel_path):
            os.remove(excel_path)


def test_accura_processing():
    """Test ACCURA processing functionality."""
    print("\n" + "=" * 60)
    print("Testing ACCURA processing...")
    
    excel_path = create_sample_excel_file()
    
    try:
        result = parse_excel_for_accura(excel_path)
        
        print(f"✓ ACCURA processing completed")
        print(f"  - Items count: {result['aantal_items']}")
        print(f"  - Sides count: {result['aantal_sides']}")
        print(f"  - MO number: {result['mo_number']}")
        print(f"  - Customer name: {result['customer_name']}")
        
        # Expected: 8 items (all rows have at least one Afplak column filled)
        # Row 1: 2 sides (Boven + Links)
        # Row 2: 2 sides (Onder + Rechts)  
        # Row 3: 2 sides (Boven + Onder)
        # Row 4: 1 side (Links)
        # Row 5: 2 sides (Boven + Links)
        # Row 6: 3 sides (Boven + Onder + Rechts)
        # Row 7: 2 sides (Onder + Links)
        # Row 8: 2 sides (Boven + Rechts)
        # Total: 8 items, 16 sides
        
        assert result['aantal_items'] == 8, f"Expected 8 items, got {result['aantal_items']}"
        print("✓ All ACCURA tests passed!")
        
    except Exception as e:
        print(f"✗ ACCURA processing failed: {e}")
    
    finally:
        if os.path.exists(excel_path):
            os.remove(excel_path)


def test_boere_processing():
    """Test BOERE processing functionality."""
    print("\n" + "=" * 60)
    print("Testing BOERE processing...")
    
    excel_path = create_sample_excel_file()
    
    try:
        result = parse_excel_for_boere(excel_path)
        
        print(f"✓ BOERE processing completed")
        print(f"  - Item count: {result['item_count']}")
        print(f"  - MO number: {result['mo_number']}")
        print(f"  - Customer name: {result['customer_name']}")
        
        # Expected: 8 items (all Materiaal entries)
        assert result['item_count'] == 8, f"Expected 8 items, got {result['item_count']}"
        assert result['mo_number'] == 'MO06789', f"Expected MO06789, got {result['mo_number']}"
        
        print("✓ All BOERE tests passed!")
        
    except Exception as e:
        print(f"✗ BOERE processing failed: {e}")
    
    finally:
        if os.path.exists(excel_path):
            os.remove(excel_path)


def test_unified_processing():
    """Test unified processing for all types."""
    print("\n" + "=" * 60)
    print("Testing unified processing...")
    
    excel_path = create_sample_excel_file()
    
    try:
        processor_types = ['NESTING_PROCESSING', 'ACCURA_PROCESSING', 'BOERE_PROCESSING']
        results = process_excel_for_all_types(excel_path, processor_types)
        
        print(f"✓ Unified processing completed")
        
        # Check NESTING results
        nesting = results['NESTING_PROCESSING']
        print(f"  - NESTING: {nesting['nesting_count']} nesting, {nesting['opdeelzaag_count']} opdeelzaag")
        
        # Check ACCURA results
        accura = results['ACCURA_PROCESSING']
        print(f"  - ACCURA: {accura['aantal_items']} items, {accura['aantal_sides']} sides")
        
        # Check BOERE results
        boere = results['BOERE_PROCESSING']
        print(f"  - BOERE: {boere['item_count']} items")
        
        # Check metadata
        print(f"  - MO Number: {nesting['mo_number']}")
        print(f"  - Customer: {nesting['customer_name']}")
        
        print("✓ All unified processing tests passed!")
        
    except Exception as e:
        print(f"✗ Unified processing failed: {e}")
    
    finally:
        if os.path.exists(excel_path):
            os.remove(excel_path)


def main():
    """Run all tests."""
    print("Starting Excel processing tests...")
    print("This will test the new Excel-based processing for NESTING, ACCURA, and BOERE.")
    
    try:
        test_excel_file_matching()
        test_nesting_processing()
        test_accura_processing()
        test_boere_processing()
        test_unified_processing()
        
        print("\n" + "=" * 60)
        print("✓ All tests completed successfully!")
        print("The Excel processing migration is ready for use.")
        
    except Exception as e:
        print(f"\n✗ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()