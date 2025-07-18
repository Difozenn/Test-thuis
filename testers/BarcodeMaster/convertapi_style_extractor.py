#!/usr/bin/env python3
"""
CONVERTAPI-STYLE EXTRACTOR
Replicate ConvertAPI's approach: IncludeFormatting=true, SingleSheet=true
"""

import subprocess
import os
import pandas as pd

def extract_with_formatting_preservation(pdf_path: str) -> str:
    """Extract PDF preserving formatting like ConvertAPI does"""
    
    print("🎯 REPLICATING CONVERTAPI APPROACH")
    print("Parameters: IncludeFormatting=true, SingleSheet=true")
    print("=" * 70)
    
    xlsx_file = pdf_path.replace('.PDF', '_convertapi_style.xlsx').replace('.pdf', '_convertapi_style.xlsx')
    
    # Method 1: LibreOffice with specific import filters
    print("\n📊 Method 1: LibreOffice with formatting preservation...")
    result = extract_with_libreoffice_formatted(pdf_path, xlsx_file)
    if result:
        return result
    
    # Method 2: Pandoc with table detection
    print("\n📊 Method 2: Pandoc with table preservation...")
    result = extract_with_pandoc_formatted(pdf_path, xlsx_file)
    if result:
        return result
    
    # Method 3: Multi-stage approach (PDF→HTML→Excel)
    print("\n📊 Method 3: PDF→HTML→Excel conversion...")
    result = extract_via_html_intermediate(pdf_path, xlsx_file)
    if result:
        return result
    
    # Method 4: Combined text + table extraction
    print("\n📊 Method 4: Combined approach...")
    result = extract_combined_approach(pdf_path, xlsx_file)
    if result:
        return result
    
    return None

def extract_with_libreoffice_formatted(pdf_path: str, xlsx_file: str) -> str:
    """Use LibreOffice with specific formatting filters"""
    
    try:
        # Try LibreOffice with Draw (better for formatted PDFs)
        cmd = [
            'libreoffice',
            '--headless',
            '--draw',
            '--convert-to', 'xlsx',
            '--outdir', os.path.dirname(xlsx_file),
            pdf_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        # Check if file was created
        temp_xlsx = pdf_path.replace('.PDF', '.xlsx').replace('.pdf', '.xlsx')
        if os.path.exists(temp_xlsx):
            # Move to target location
            os.rename(temp_xlsx, xlsx_file)
            print(f"✅ LibreOffice Draw extraction: {xlsx_file}")
            return xlsx_file
        
        print(f"❌ LibreOffice Draw failed: {result.stderr}")
        return None
    
    except Exception as e:
        print(f"❌ LibreOffice error: {e}")
        return None

def extract_with_pandoc_formatted(pdf_path: str, xlsx_file: str) -> str:
    """Use Pandoc with table detection"""
    
    try:
        # Pandoc with table extraction
        cmd = [
            'pandoc',
            pdf_path,
            '-o', xlsx_file,
            '--extract-media=.',
            '--table-to-csv'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0 and os.path.exists(xlsx_file):
            print(f"✅ Pandoc extraction: {xlsx_file}")
            return xlsx_file
        
        print(f"❌ Pandoc failed: {result.stderr}")
        return None
    
    except Exception as e:
        print(f"❌ Pandoc error: {e}")
        return None

def extract_via_html_intermediate(pdf_path: str, xlsx_file: str) -> str:
    """Convert PDF→HTML→Excel to preserve formatting"""
    
    try:
        # Step 1: PDF to HTML (preserves layout)
        html_file = pdf_path.replace('.PDF', '_temp.html').replace('.pdf', '_temp.html')
        
        cmd = ['pdftohtml', '-s', '-c', pdf_path, html_file.replace('.html', '')]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if not os.path.exists(html_file):
            print("❌ PDF to HTML conversion failed")
            return None
        
        # Step 2: HTML to Excel (preserves tables)
        print("   Converting HTML to Excel...")
        
        # Read HTML tables
        dfs = pd.read_html(html_file, header=None)
        
        if dfs:
            # Combine all tables into single sheet (SingleSheet=true)
            combined_data = []
            
            for i, df in enumerate(dfs):
                # Add separator between tables
                if i > 0:
                    combined_data.append(pd.DataFrame([[''] * df.shape[1]]))
                
                combined_data.append(df)
            
            # Create single sheet Excel
            final_df = pd.concat(combined_data, ignore_index=True)
            final_df.to_excel(xlsx_file, index=False, header=False)
            
            # Cleanup
            os.remove(html_file)
            
            print(f"✅ HTML intermediate extraction: {xlsx_file}")
            return xlsx_file
        
        print("❌ No tables found in HTML")
        return None
    
    except Exception as e:
        print(f"❌ HTML intermediate error: {e}")
        return None

def extract_combined_approach(pdf_path: str, xlsx_file: str) -> str:
    """Combined text + table extraction (like ConvertAPI)"""
    
    try:
        print("   Extracting text content...")
        
        # Get all text with layout preservation
        cmd = ['pdftotext', '-layout', pdf_path, '-']
        text_result = subprocess.run(cmd, capture_output=True, text=True)
        
        if text_result.returncode != 0:
            print("❌ Text extraction failed")
            return None
        
        # Get table data with Camelot
        print("   Extracting table data...")
        import camelot
        
        tables = camelot.read_pdf(pdf_path, flavor='lattice', pages='all')
        
        # Combine text and tables in single sheet
        all_content = []
        
        # Add text content first
        text_lines = text_result.stdout.split('\n')
        for line in text_lines[:50]:  # First 50 lines
            if line.strip():
                all_content.append([line.strip()])
        
        # Add separator
        all_content.append(['=== EXTRACTED TABLES ==='])
        
        # Add table data
        if tables:
            for i, table in enumerate(tables):
                all_content.append([f'--- Table {i+1} (Page {table.page}) ---'])
                
                # Add table data
                df = table.df
                for _, row in df.iterrows():
                    all_content.append(row.tolist())
                
                all_content.append([''])  # Empty row between tables
        
        # Create Excel file
        if all_content:
            final_df = pd.DataFrame(all_content)
            final_df.to_excel(xlsx_file, index=False, header=False)
            
            print(f"✅ Combined extraction: {xlsx_file}")
            return xlsx_file
        
        print("❌ No content extracted")
        return None
    
    except Exception as e:
        print(f"❌ Combined approach error: {e}")
        return None

def analyze_convertapi_style_output(xlsx_file: str):
    """Analyze the ConvertAPI-style output"""
    
    if not os.path.exists(xlsx_file):
        return
    
    print(f"\n📈 ANALYZING OUTPUT: {os.path.basename(xlsx_file)}")
    
    try:
        # Read Excel file
        df = pd.read_excel(xlsx_file, header=None)
        
        print(f"   Size: {len(df)} rows × {len(df.columns)} columns")
        
        # Look for key patterns
        content = df.to_string().lower()
        
        patterns = {
            'nesting': content.count('nesting'),
            'opdeelzaag': content.count('opdeelzaag'),
            'aantal_onderdelen': content.count('aantal onderdelen'),
            'controle': content.count('controle'),
            'magazijn': content.count('magazijn'),
            'beschrijving': content.count('beschrijving'),
            'fineer': content.count('fineer'),
        }
        
        print("   Key patterns found:")
        for pattern, count in patterns.items():
            if count > 0:
                print(f"     - {pattern}: {count}")
        
        # Show sample content
        print("   Sample content (first 5 rows):")
        for i in range(min(5, len(df))):
            row_text = ' | '.join([str(cell)[:30] for cell in df.iloc[i].values[:3]])
            print(f"     {i}: {row_text}...")
    
    except Exception as e:
        print(f"   Analysis failed: {e}")

def test_convertapi_style():
    """Test ConvertAPI-style extraction"""
    
    pdf_path = 'S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF'
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    # Extract with ConvertAPI-style approach
    result_file = extract_with_formatting_preservation(pdf_path)
    
    if result_file:
        # Analyze the output
        analyze_convertapi_style_output(result_file)
        
        file_size = os.path.getsize(result_file)
        print(f"\n✅ ConvertAPI-style extraction completed!")
        print(f"File: {result_file} ({file_size} bytes)")
        print("This should have similar quality to ConvertAPI output.")
    else:
        print("\n❌ ConvertAPI-style extraction failed")
        print("Consider trying the actual ConvertAPI service for best results.")

if __name__ == "__main__":
    test_convertapi_style()