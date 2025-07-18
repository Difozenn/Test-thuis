#!/usr/bin/env python3
"""
Debug script to inspect PDF database contents
"""

import sqlite3
import json
import os

def debug_pdf_database():
    """Debug PDF database contents."""
    # Check multiple possible database locations
    possible_paths = [
        '/home/difusion/Projects/BarcodeMaster/pdf_cache.db',
        '/home/difusion/Projects/BarcodeMaster/database/pdf_cache.db',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pdf_cache.db')
    ]
    
    db_path = None
    for path in possible_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print("❌ No PDF cache database found in expected locations")
        return
    
    print("PDF Database Debug")
    print("==================")
    print(f"Database: {db_path}\n")
    
    try:
        with sqlite3.connect(db_path) as conn:
            # Check pdf_documents table
            cursor = conn.execute("SELECT * FROM pdf_documents")
            docs = cursor.fetchall()
            print(f"📄 PDF Documents: {len(docs)} records")
            for doc in docs:
                print(f"  ID: {doc[0]}, File: {doc[1]}")
                print(f"  Project: {doc[2]}, Pages: {doc[6]}, Success: {doc[7]}")
            
            # Check pdf_table_data summary
            cursor = conn.execute("""
                SELECT pdf_id, section_type, COUNT(*) as row_count 
                FROM pdf_table_data 
                GROUP BY pdf_id, section_type
                ORDER BY pdf_id, section_type
            """)
            print(f"\n📊 Table Data Summary:")
            for row in cursor.fetchall():
                print(f"  PDF {row[0]}, Section: {row[1]}, Rows: {row[2]}")
            
            # Check specific data for each section
            print(f"\n🔍 Detailed Data Inspection:")
            
            # Nesting data
            cursor = conn.execute("""
                SELECT item_number, onderdeel, l1, l2, b1, b2 
                FROM pdf_table_data 
                WHERE section_type = 'Nesting' 
                LIMIT 5
            """)
            print(f"\n[Nesting] Sample rows:")
            for row in cursor.fetchall():
                print(f"  Item {row[0]}: {row[1]}, L1={row[2]}, L2={row[3]}, B1={row[4]}, B2={row[5]}")
            
            # Opdeelzaag data
            cursor = conn.execute("""
                SELECT item_number, onderdeel, l1, l2, b1, b2 
                FROM pdf_table_data 
                WHERE section_type = 'Opdeelzaag' 
                LIMIT 5
            """)
            print(f"\n[Opdeelzaag] Sample rows:")
            for row in cursor.fetchall():
                print(f"  Item {row[0]}: {row[1]}, L1={row[2]}, L2={row[3]}, B1={row[4]}, B2={row[5]}")
            
            # Controle data
            cursor = conn.execute("""
                SELECT item_number, onderdeel, pro_methode 
                FROM pdf_table_data 
                WHERE section_type = 'Controle' 
                LIMIT 5
            """)
            print(f"\n[Controle] Sample rows:")
            for row in cursor.fetchall():
                print(f"  Item {row[0]}: {row[1]}, Pro.methode={row[2]}")
            
            # Check for NULL item_numbers
            cursor = conn.execute("""
                SELECT section_type, COUNT(*) 
                FROM pdf_table_data 
                WHERE item_number IS NULL 
                GROUP BY section_type
            """)
            print(f"\n⚠️  Rows with NULL item_number:")
            for row in cursor.fetchall():
                print(f"  {row[0]}: {row[1]} rows")
            
            # Check unique project codes
            cursor = conn.execute("SELECT DISTINCT project_code FROM pdf_documents")
            print(f"\n📁 Project codes in database:")
            for row in cursor.fetchall():
                print(f"  '{row[0]}'")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_pdf_database()