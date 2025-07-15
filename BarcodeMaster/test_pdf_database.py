#!/usr/bin/env python3
"""
Test script for PDF database functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf_database_manager import PDFDatabaseManager

def test_pdf_database():
    """Test PDF database parsing and querying."""
    print("PDF Database Test")
    print("=================")
    
    # Initialize PDF database manager
    try:
        pdf_manager = PDFDatabaseManager()
        print("✅ PDF database manager initialized")
    except Exception as e:
        print(f"❌ Failed to initialize PDF database manager: {e}")
        return
    
    # Test PDF path
    pdf_path = "/home/difusion/Projects/BarcodeMaster/S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF"
    project_code = "MO07199_Hoekdressing - opklapbed (4-7)"
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF file not found: {pdf_path}")
        return
    
    print(f"\n📄 Testing PDF: {os.path.basename(pdf_path)}")
    print(f"📋 Project Code: {project_code}")
    
    # Check if already cached
    is_cached = pdf_manager.is_pdf_cached(pdf_path, project_code)
    print(f"💾 Already cached: {is_cached}")
    
    if not is_cached:
        print("\n🔄 Parsing and storing PDF...")
        success = pdf_manager.parse_and_store_pdf(pdf_path, project_code)
        if success:
            print("✅ PDF parsed and stored successfully")
        else:
            print("❌ Failed to parse and store PDF")
            return
    else:
        print("\n💾 Using cached PDF data")
    
    # Test ACCURA data
    print("\n🔍 Testing ACCURA data...")
    accura_data = pdf_manager.get_accura_data(project_code)
    print(f"ACCURA Results: {accura_data['aantal_items']} items, {accura_data['aantal_sides']} sides")
    
    # Test BOERE data
    print("\n🔍 Testing BOERE data...")
    boere_count = pdf_manager.get_boere_data(project_code)
    print(f"BOERE Results: {boere_count} items")
    
    # Test NESTING data
    print("\n🔍 Testing NESTING data...")
    nesting_data = pdf_manager.get_nesting_data(project_code)
    print(f"NESTING Results: Nesting={nesting_data['nesting_count']}, Opdeelzaag={nesting_data['opdeelzaag_count']}")
    
    print("\n" + "="*50)
    print("SUMMARY:")
    print(f"ACCURA: {accura_data['aantal_items']} items, {accura_data['aantal_sides']} sides")
    print(f"BOERE: {boere_count} items")
    print(f"NESTING: {nesting_data['nesting_count']} items")
    print(f"OPDEELZAAG: {nesting_data['opdeelzaag_count']} items")
    
    # Expected results validation
    print("\n🎯 Expected vs Actual:")
    print(f"ACCURA: Expected ~40+ items → Got {accura_data['aantal_items']} items")
    print(f"BOERE: Expected 61 items → Got {boere_count} items")
    print(f"NESTING: Expected 38 items → Got {nesting_data['nesting_count']} items")
    print(f"OPDEELZAAG: Expected 14 items → Got {nesting_data['opdeelzaag_count']} items")

if __name__ == "__main__":
    test_pdf_database()