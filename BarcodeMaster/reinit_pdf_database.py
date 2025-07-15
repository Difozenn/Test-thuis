#!/usr/bin/env python3
"""
Reinitialize and test PDF database
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf_database_manager import PDFDatabaseManager

def reinit_and_test():
    """Reinitialize database and test with sample PDF."""
    print("PDF Database Reinitialization")
    print("=============================")
    
    # Initialize database manager (will create tables)
    manager = PDFDatabaseManager()
    print(f"✅ Database initialized at: {manager.db_path}")
    
    # Test PDF
    pdf_path = "C:/Rapporten/S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF"
    project_code = "S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7)"
    
    # Windows path handling
    pdf_path = pdf_path.replace('/', '\\')
    
    print(f"\n📄 Testing with PDF: {os.path.basename(pdf_path)}")
    print(f"📋 Project code: {project_code}")
    
    # Parse and store
    if os.path.exists(pdf_path):
        print("\n🔄 Parsing PDF...")
        success = manager.parse_and_store_pdf(pdf_path, project_code)
        print(f"✅ Parse success: {success}")
        
        if success:
            # Test queries
            print("\n📊 Testing queries:")
            
            accura = manager.get_accura_data(project_code)
            print(f"ACCURA: {accura['aantal_items']} items, {accura['aantal_sides']} sides")
            
            boere = manager.get_boere_data(project_code)
            print(f"BOERE: {boere} items")
            
            nesting = manager.get_nesting_data(project_code)
            print(f"NESTING: {nesting['nesting_count']} items")
            print(f"OPDEELZAAG: {nesting['opdeelzaag_count']} items")
    else:
        print(f"❌ PDF not found at: {pdf_path}")

if __name__ == "__main__":
    reinit_and_test()