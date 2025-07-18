#!/usr/bin/env python3
"""
EXCEL OUTPUT EXTRACTOR
Convert PDF extraction results to Excel format with proper sheets
"""

import pandas as pd
import os

def convert_tabula_to_excel():
    """Convert Tabula CSV to Excel with multiple sheets"""
    
    csv_file = 'S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7)_tabula.csv'
    excel_file = csv_file.replace('.csv', '.xlsx')
    
    if not os.path.exists(csv_file):
        print(f"❌ Tabula CSV not found: {csv_file}")
        return None
    
    print(f"📊 Converting Tabula CSV to Excel...")
    
    try:
        # Read CSV
        df = pd.read_csv(csv_file)
        
        # Create Excel with multiple sheets based on content
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            
            # Sheet 1: All data
            df.to_excel(writer, sheet_name='All_Data', index=False)
            
            # Sheet 2: Only numbered rows (table data)
            numbered_rows = df[df.iloc[:, 0].astype(str).str.match(r'^\d+$', na=False)]
            if not numbered_rows.empty:
                numbered_rows.to_excel(writer, sheet_name='Numbered_Items', index=False)
            
            # Sheet 3: Headers and section markers
            headers = df[df.astype(str).apply(lambda x: x.str.contains('aantal onderdelen|nesting|controle|magazijn', case=False, na=False)).any(axis=1)]
            if not headers.empty:
                headers.to_excel(writer, sheet_name='Section_Headers', index=False)
            
            # Sheet 4: Items with edge processing (ACCURA candidates)
            edge_items = df[df.astype(str).apply(lambda x: x.str.contains('fineer|finger|l1|l2|b1|b2', case=False, na=False)).any(axis=1)]
            if not edge_items.empty:
                edge_items.to_excel(writer, sheet_name='Edge_Processing', index=False)
        
        print(f"✅ Excel file created: {excel_file}")
        return excel_file
    
    except Exception as e:
        print(f"❌ Excel conversion failed: {e}")
        return None

def convert_excalibur_to_excel():
    """Convert Excalibur CSV to Excel with table separation"""
    
    csv_file = 'S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7)_excalibur_lattice.csv'
    excel_file = csv_file.replace('.csv', '.xlsx')
    
    if not os.path.exists(csv_file):
        print(f"❌ Excalibur CSV not found: {csv_file}")
        return None
    
    print(f"📊 Converting Excalibur CSV to Excel...")
    
    try:
        # Read CSV
        df = pd.read_csv(csv_file)
        
        # Create Excel with separate sheets per table
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            
            # Sheet 1: All data
            df.to_excel(writer, sheet_name='All_Tables', index=False)
            
            # Separate sheets per table number
            if '_table_num' in df.columns:
                for table_num in df['_table_num'].unique():
                    if pd.notna(table_num):
                        table_data = df[df['_table_num'] == table_num].copy()
                        # Remove metadata columns for cleaner view
                        table_data = table_data.drop(['_table_num', '_page', '_accuracy'], axis=1, errors='ignore')
                        
                        sheet_name = f'Table_{int(table_num)}'
                        table_data.to_excel(writer, sheet_name=sheet_name, index=False)
        
        print(f"✅ Excel file created: {excel_file}")
        return excel_file
    
    except Exception as e:
        print(f"❌ Excel conversion failed: {e}")
        return None

def create_excel_with_tabula_java():
    """Use Tabula-java to directly create Excel output"""
    
    pdf_path = 'S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF'
    excel_file = pdf_path.replace('.PDF', '_tabula_direct.xlsx').replace('.pdf', '_tabula_direct.xlsx')
    jar_file = 'tabula-java.jar'
    
    if not os.path.exists(jar_file):
        print(f"❌ Tabula JAR not found: {jar_file}")
        return None
    
    print(f"📊 Creating Excel directly with Tabula-java...")
    
    try:
        import subprocess
        
        # Use Tabula-java to create Excel directly
        cmd = [
            'java', '-jar', jar_file,
            '-o', excel_file,
            '-f', 'XLSX',  # Excel format
            '-p', 'all',
            '-l',  # Lattice mode
            pdf_path
        ]
        
        print(f"   Running: {' '.join(cmd[:6])}...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0 and os.path.exists(excel_file):
            file_size = os.path.getsize(excel_file)
            print(f"✅ Tabula Excel created: {excel_file} ({file_size} bytes)")
            return excel_file
        else:
            print(f"❌ Tabula Excel creation failed")
            print(f"   Error: {result.stderr}")
            return None
    
    except Exception as e:
        print(f"❌ Tabula Excel error: {e}")
        return None

def analyze_excel_file(excel_file: str):
    """Analyze Excel file structure"""
    
    if not os.path.exists(excel_file):
        return
    
    print(f"\n📈 ANALYZING EXCEL: {os.path.basename(excel_file)}")
    
    try:
        # Read all sheets
        excel_data = pd.read_excel(excel_file, sheet_name=None)
        
        print(f"   Sheets: {len(excel_data)}")
        
        for sheet_name, df in excel_data.items():
            print(f"   📋 {sheet_name}: {len(df)} rows × {len(df.columns)} cols")
            
            # Check for key patterns
            content = df.to_string().lower()
            patterns = []
            if 'aantal onderdelen' in content: patterns.append('aantal_onderdelen')
            if 'nesting' in content: patterns.append('nesting')
            if 'controle' in content: patterns.append('controle')
            if 'fineer' in content: patterns.append('fineer')
            
            if patterns:
                print(f"       Patterns: {', '.join(patterns)}")
    
    except Exception as e:
        print(f"   Analysis failed: {e}")

def test_excel_outputs():
    """Test all Excel output methods"""
    
    print("📊 CREATING EXCEL OUTPUTS FROM PDF EXTRACTIONS")
    print("=" * 70)
    
    results = []
    
    # Method 1: Convert Tabula CSV to Excel
    print("\n📊 Method 1: Tabula CSV → Excel...")
    tabula_excel = convert_tabula_to_excel()
    if tabula_excel:
        analyze_excel_file(tabula_excel)
        results.append(('Tabula CSV→Excel', tabula_excel))
    
    # Method 2: Convert Excalibur CSV to Excel  
    print("\n📊 Method 2: Excalibur CSV → Excel...")
    excalibur_excel = convert_excalibur_to_excel()
    if excalibur_excel:
        analyze_excel_file(excalibur_excel)
        results.append(('Excalibur CSV→Excel', excalibur_excel))
    
    # Method 3: Direct Excel from Tabula-java
    print("\n📊 Method 3: Tabula-java direct Excel...")
    direct_excel = create_excel_with_tabula_java()
    if direct_excel:
        analyze_excel_file(direct_excel)
        results.append(('Tabula Direct Excel', direct_excel))
    
    # Summary
    print(f"\n🏆 EXCEL OUTPUT SUMMARY:")
    if results:
        for method, file in results:
            file_size = os.path.getsize(file)
            print(f"  ✅ {method}: {file} ({file_size} bytes)")
        
        print(f"\n🎯 You now have {len(results)} Excel files to choose from!")
        return results
    else:
        print("❌ No Excel files created")
        return []

if __name__ == "__main__":
    results = test_excel_outputs()
    
    if results:
        print(f"\n✅ Excel output generation completed!")
        print("These Excel files should be easier to work with than CSV.")
    else:
        print("\n❌ Excel output generation failed")