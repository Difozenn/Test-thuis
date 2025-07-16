#!/usr/bin/env python3
"""
Simple PDF to Excel converter - Creates the Excel file and keeps it
"""

import tabula
import pandas as pd

def convert_pdf_to_excel(pdf_path: str, excel_path: str):
    """Convert PDF to Excel and save it"""
    
    print(f"🔄 Converting {pdf_path} to Excel...")
    
    try:
        # Extract all tables from relevant pages
        dfs = tabula.read_pdf(
            pdf_path,
            pages="2-7,11-25",  # Nesting/Opdeelzaag + BOERE pages
            multiple_tables=True,
            pandas_options={'header': None}
        )
        
        if dfs:
            # Save to Excel file
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                for i, df in enumerate(dfs):
                    if not df.empty:
                        df.to_excel(writer, sheet_name=f'Table_{i}', index=False, header=False)
            
            print(f"✅ Excel file created: {excel_path}")
            print(f"📊 {len(dfs)} tables extracted")
            return excel_path
        else:
            print("❌ No tables found")
            return None
            
    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        return None

if __name__ == "__main__":
    pdf_file = 'S04479_RAPPORT_Rudi Matterne_0411_MO07202-7203_TV-wand (7-7).PDF'
    excel_file = 'extracted_tables.xlsx'
    
    result = convert_pdf_to_excel(pdf_file, excel_file)
    
    if result:
        print(f"\n🎯 Excel file ready: {excel_file}")
        print("Now you can open it and see all the extracted tables!")
    else:
        print("\n❌ Failed to create Excel file")