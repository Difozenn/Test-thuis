#!/usr/bin/env python3
"""
TABULA PDF TABLE EXTRACTOR
Using Tabula-java for automated PDF table extraction
"""

import subprocess
import os
import requests
import zipfile

def download_tabula_jar():
    """Download Tabula JAR file if not present"""
    
    jar_file = 'tabula-java.jar'
    
    if os.path.exists(jar_file):
        print(f"✅ Tabula JAR already exists: {jar_file}")
        return jar_file
    
    print("📥 Downloading Tabula JAR...")
    
    try:
        # Download latest Tabula JAR from GitHub releases
        url = "https://github.com/tabulapdf/tabula-java/releases/download/v1.0.5/tabula-1.0.5-jar-with-dependencies.jar"
        
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        
        with open(jar_file, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ Tabula JAR downloaded: {jar_file}")
        return jar_file
    
    except Exception as e:
        print(f"❌ Failed to download Tabula JAR: {e}")
        return None

def extract_tables_with_tabula(pdf_path: str, jar_file: str) -> str:
    """Extract tables using Tabula-java"""
    
    print(f"📊 Extracting tables with Tabula...")
    
    csv_file = pdf_path.replace('.PDF', '_tabula.csv').replace('.pdf', '_tabula.csv')
    
    try:
        # Use Tabula-java to extract all tables
        cmd = [
            'java', '-jar', jar_file,
            '-o', csv_file,
            '-f', 'CSV',
            '-p', 'all',
            '-l',  # Lattice mode for tables with borders
            pdf_path
        ]
        
        print(f"   Running: {' '.join(cmd[:6])}...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0 and os.path.exists(csv_file):
            file_size = os.path.getsize(csv_file)
            print(f"✅ Tabula extraction successful: {csv_file} ({file_size} bytes)")
            
            # Show sample of extracted data
            with open(csv_file, 'r', encoding='utf-8') as f:
                sample = f.read(500)
                print(f"   Sample data: {sample[:100]}...")
            
            return csv_file
        else:
            print(f"❌ Tabula extraction failed")
            print(f"   Return code: {result.returncode}")
            print(f"   Error: {result.stderr}")
            return None
    
    except subprocess.TimeoutExpired:
        print("⏰ Tabula extraction timeout")
        return None
    except Exception as e:
        print(f"❌ Tabula extraction error: {e}")
        return None

def extract_tables_stream_mode(pdf_path: str, jar_file: str) -> str:
    """Extract tables using Tabula stream mode (for tables without borders)"""
    
    print(f"📊 Extracting tables with Tabula (stream mode)...")
    
    csv_file = pdf_path.replace('.PDF', '_tabula_stream.csv').replace('.pdf', '_tabula_stream.csv')
    
    try:
        # Use stream mode for tables without clear borders
        cmd = [
            'java', '-jar', jar_file,
            '-o', csv_file,
            '-f', 'CSV',
            '-p', 'all',
            pdf_path  # No -l flag = stream mode
        ]
        
        print(f"   Running stream mode...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0 and os.path.exists(csv_file):
            file_size = os.path.getsize(csv_file)
            print(f"✅ Tabula stream extraction successful: {csv_file} ({file_size} bytes)")
            return csv_file
        else:
            print(f"❌ Tabula stream extraction failed")
            return None
    
    except Exception as e:
        print(f"❌ Tabula stream extraction error: {e}")
        return None

def analyze_tabula_csv(csv_file: str):
    """Analyze the quality of Tabula CSV output"""
    
    if not os.path.exists(csv_file):
        return
    
    print(f"\n📈 ANALYZING: {os.path.basename(csv_file)}")
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = [l.strip() for l in content.split('\n') if l.strip()]
        
        # Count key patterns
        patterns = {
            'total_lines': len(lines),
            'nesting': content.lower().count('nesting'),
            'aantal_onderdelen': content.lower().count('aantal onderdelen'),
            'controle': content.lower().count('controle'),
            'magazijn': content.lower().count('magazijn'),
            'beschrijving': content.lower().count('beschrijving'),
            'fineer': content.lower().count('fineer'),
            'numbered_lines': len([l for l in lines if l.split(',')[0].strip().isdigit()]),
        }
        
        print(f"   Lines: {patterns['total_lines']}")
        print(f"   Numbered rows: {patterns['numbered_lines']}")
        print(f"   Key patterns found:")
        for pattern, count in patterns.items():
            if pattern not in ['total_lines', 'numbered_lines'] and count > 0:
                print(f"     - {pattern}: {count}")
        
        # Quality score
        quality = 0
        if patterns['total_lines'] > 50: quality += 2
        if patterns['numbered_lines'] > 10: quality += 2
        if patterns['aantal_onderdelen'] > 0: quality += 3
        if patterns['nesting'] > 0: quality += 2
        if patterns['controle'] > 0: quality += 1
        
        print(f"   Quality score: {quality}/10")
        
        return patterns
    
    except Exception as e:
        print(f"   Analysis failed: {e}")
        return None

def test_tabula_extraction():
    """Test Tabula PDF table extraction"""
    
    pdf_path = 'S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF'
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print("📋 TESTING TABULA PDF TABLE EXTRACTION")
    print("=" * 70)
    
    # Download Tabula JAR
    jar_file = download_tabula_jar()
    if not jar_file:
        print("❌ Cannot get Tabula JAR file")
        return
    
    # Check Java
    try:
        result = subprocess.run(['java', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Java is available")
        else:
            print("❌ Java not found")
            return
    except FileNotFoundError:
        print("❌ Java not installed")
        return
    
    results = []
    
    # Method 1: Lattice mode (for tables with borders)
    print(f"\n📊 Method 1: Lattice mode...")
    lattice_file = extract_tables_with_tabula(pdf_path, jar_file)
    if lattice_file:
        lattice_analysis = analyze_tabula_csv(lattice_file)
        results.append(('Lattice', lattice_file, lattice_analysis))
    
    # Method 2: Stream mode (for tables without borders)  
    print(f"\n📊 Method 2: Stream mode...")
    stream_file = extract_tables_stream_mode(pdf_path, jar_file)
    if stream_file:
        stream_analysis = analyze_tabula_csv(stream_file)
        results.append(('Stream', stream_file, stream_analysis))
    
    # Compare results
    print(f"\n🏆 TABULA RESULTS SUMMARY:")
    if results:
        for mode, file, analysis in results:
            quality = analysis.get('quality', 0) if analysis else 0
            print(f"  {mode} mode: {file} (quality: {quality}/10)")
        
        # Recommend best result
        best = max(results, key=lambda x: x[2].get('quality', 0) if x[2] else 0)
        print(f"\n🎯 RECOMMENDED: {best[0]} mode - {best[1]}")
        return best[1]
    else:
        print("❌ No successful extractions")
        return None

if __name__ == "__main__":
    result = test_tabula_extraction()
    
    if result:
        print(f"\n✅ Tabula extraction completed!")
        print(f"Best result: {result}")
        print("You can now analyze this CSV file for exact counts.")
    else:
        print("\n❌ Tabula extraction failed")
        print("Consider trying other methods.")