#!/usr/bin/env python3
"""
Test ACCURA and BOERE processing using the actual PDF text content
"""

def test_accura_from_text(pdf_text):
    """Test ACCURA processing on text content."""
    print("=== Testing ACCURA Processing ===")
    
    lines = pdf_text.split('\n')
    aantal_items = 0
    aantal_sides = 0
    
    # Look for Nesting and Opdeelzaag sections
    in_nesting = False
    in_opdeelzaag = False
    current_section = None
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        line_upper = line_stripped.upper()
        
        # Detect section headers
        if 'NESTING' in line_upper:
            in_nesting = True
            in_opdeelzaag = False
            current_section = "Nesting"
            print(f"\n📍 Entering {current_section} section")
            continue
        elif 'OPDEELZAAG' in line_upper:
            in_nesting = False
            in_opdeelzaag = True
            current_section = "Opdeelzaag"
            print(f"\n📍 Entering {current_section} section")
            continue
        elif any(keyword in line_upper for keyword in ['CONTROLE', 'MASSIEF', 'MAGAZIJN']):
            in_nesting = False
            in_opdeelzaag = False
            if current_section:
                print(f"📍 Exiting {current_section} section")
            current_section = None
            continue
        
        # Process data lines in ACCURA sections
        if (in_nesting or in_opdeelzaag) and current_section:
            # Look for numbered data rows with L1/L2/B1/B2 content
            if line_stripped and line_stripped[0].isdigit():
                parts = line_stripped.split()
                if len(parts) >= 10:  # Enough columns for L1/L2/B1/B2
                    print(f"\n{current_section} Row: {line_stripped[:100]}...")
                    
                    # Count meaningful content in what should be L1/L2/B1/B2 positions
                    # Based on the PDF structure, these are typically columns 5-8
                    sides_in_row = 0
                    has_work = False
                    
                    # Check positions that likely contain L1/L2/B1/B2 content
                    l1_l2_b1_b2_content = []
                    if len(parts) >= 8:
                        # Look for content around positions 5-8 (approximate L1/L2/B1/B2)
                        for col_idx in range(5, min(9, len(parts))):
                            if col_idx < len(parts):
                                content = parts[col_idx]
                                l1_l2_b1_b2_content.append(content)
                                
                                # Check if meaningful content
                                if (content and content.upper() not in ['', 'STANDAARD', 'TE', 'BESTELLEN'] 
                                    and not content.isdigit() and len(content) > 1):
                                    sides_in_row += 1
                                    has_work = True
                                    print(f"  ✓ Found work content in col {col_idx}: '{content}'")
                    
                    print(f"  L1/L2/B1/B2 area content: {l1_l2_b1_b2_content}")
                    
                    if has_work:
                        aantal_items += 1
                        aantal_sides += sides_in_row
                        print(f"  ✅ {current_section} item {aantal_items}: {sides_in_row} sides with work")
                    else:
                        print(f"  ❌ No work content in L1/L2/B1/B2 columns")
    
    print(f"\n🎯 ACCURA Final Result: {aantal_items} items, {aantal_sides} sides")
    return aantal_items, aantal_sides

def test_boere_from_text(pdf_text):
    """Test BOERE processing on text content - exclude 'Te bestellen' items."""
    print("\n=== Testing BOERE Processing (Excluding 'Te bestellen') ===")
    
    lines = pdf_text.split('\n')
    total_items = 0
    
    in_controle = False
    current_table_items = []
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        line_upper = line_stripped.upper()
        
        # Detect Controle section
        if 'CONTROLE' in line_upper:
            in_controle = True
            print(f"\n📍 Entering Controle section")
            current_table_items = []
            continue
        elif any(keyword in line_upper for keyword in ['MAGAZIJN', 'NESTING', 'OPDEELZAAG', 'MASSIEF']):
            if in_controle:
                print(f"📍 Exiting Controle section")
            in_controle = False
            current_table_items = []
            continue
        
        # Process data rows in Controle sections
        if in_controle and line_stripped and line_stripped[0].isdigit():
            parts = line_stripped.split()
            if len(parts) >= 5:  # Enough parts for a meaningful row
                item_num = parts[0]
                
                # Look for Pro.methode content (usually towards the end)
                # In the structure: N° Onderdeel ... Pro.methode L1
                pro_methode_content = ""
                
                # Check if "Te bestellen" appears in the line
                if 'TE BESTELLEN' in line_upper:
                    pro_methode_content = "Te bestellen"
                    print(f"❌ Excluding item {item_num}: Pro.methode = 'Te bestellen'")
                    print(f"   Line: {line_stripped[:80]}...")
                else:
                    # Look for other Pro.methode values like "Reichenbacher", "Gannomat", etc.
                    known_methods = ['REICHENBACHER', 'GANNOMAT', 'STANDAARD']
                    for method in known_methods:
                        if method in line_upper:
                            pro_methode_content = method.capitalize()
                            break
                    
                    if not pro_methode_content:
                        pro_methode_content = "Unknown"
                    
                    total_items += 1
                    print(f"✅ Including item {item_num}: Pro.methode = '{pro_methode_content}' (Total: {total_items})")
                    print(f"   Line: {line_stripped[:80]}...")
        
        # Also check for section totals for verification
        elif in_controle and 'AANTAL ONDERDELEN:' in line_upper:
            import re
            match = re.search(r'AANTAL ONDERDELEN[:\s]*(\d+)', line_upper)
            if match:
                section_total = int(match.group(1))
                print(f"📊 Section total: {section_total} items")
    
    print(f"\n🎯 BOERE Final Result: {total_items} items (excluding 'Te bestellen')")
    return total_items

# Test with the provided PDF content
pdf_content = """Page 1 of 21
Naam: .../...
Naam: .../...
MO07199
Opus:
Macro deursensors
S8
Opmerkingen:
Accura:
Schuren
Project: 0411_MO07199_Hoekdressing - opklapbed (4-7)
info:
kopie: terugbezorgen na schuren!
Cel schuren:
Cel Massief:
Klant: Rudi Matterne
Tekenaar:
Datum:
S04479
Totaal aantal onderdelen:
JW
Kasten monteren! onderdelen sorteren per object
Vlakstraat: gekleurde sjang gebruiken.
Enkel als aangevinkt. Handwerk voor het schuren.
Cel Holzer:
Afwerking: Lakstraat
0411_MO07199_Hoekdressing - opklapbed (4-7) Page 2 of 21
MO07199
Project:
S8
Schuren
Klant: Rudi Matterne
Tekenaar: JW
Sales nr: S04479
0411_MO07199_Hoekdressing - opklapbed (4-7) Nesting
N° Onderdeel Materiaal Lengte Breedte Dikte L1 L2 B1 B2 ProductieM. Opmerkingen
1 AZ HSP 23mm BxB 2571 1023.667 23 Standaard Dik Fineer eik 1mm Fineer eik 1mm Fineer eik 1mm Fineer eik 1mm
2 LZ_01 HSP 23mm BxB 2571 510 23 Standaard Dik Fineer eik 1mm Fineer eik 1mm Fineer eik 1mm Fineer eik 1mm
14 RG MDF 19mm AFQMxB 2118 1007.7 19 Standaard
15 Front MDF 23mm AFQMxB 2086 970 23 Standaard Dik Fineer eik 1mm Fineer eik 1mm Fineer eik 1mm Fineer eik 1mm
Aantal onderdelen: 38
0411_MO07199_Hoekdressing - opklapbed (4-7) Page 4 of 21
0411_MO07199_Hoekdressing - opklapbed (4-7) Opdeelzaag
N° Onderdeel Materiaal Lengte Breedte Dikte L1 L2 B1 B2 Opmerkingen
1 BC HSP 19mm BxB 1030 507 19 Fineer eik 1mm Fineer eik 1mm
2 LZ HSP 19mm BxB 430 507 19 Fineer eik 1mm Fineer eik 1mm Fineer eik 1mm Fineer eik 1mm
5 Ruglat MDF 19-18mm Uitval 861.667 100 19
8 Klapdeur MDF 19mm AFQMxB 426 1055 19 Fineer eik 1mm Fineer eik 1mm Fineer eik 1mm Fineer eik 1mm
Aantal onderdelen: 14
Controle
BK_01
N° Onderdeel L2 B1 B2 commentaar Commentaar: Materiaal Lengte Breedte Dikte Pro.methode L1
1 Opklapscharnieren duo lift FORTE Dummy 10mm 200 90 10 Te bestellen 1 set
2 BC HSP 19mm BxB 1030 507 19 Fineer eik 1mm Fineer eik 1mm Reichenbacher
Aantal onderdelen: 7
IND_01
N° Onderdeel L2 B1 B2 commentaar Commentaar: Materiaal Lengte Breedte Dikte Pro.methode L1
1 Hangbaar_ZWART Metaal 15mm 852.667 30 15 Te bestellen
Aantal onderdelen: 1
MW_01
Aantal onderdelen: 13
MW_02
Aantal onderdelen: 17
Magazijn
N° Beschrijving Aantal stuks GB nummer
1 3delig verbindingsbeslag 10 GB00030944
Aantal onderdelen: 37"""

if __name__ == "__main__":
    print("PDF Text Analysis Test")
    print("=====================")
    
    # Test ACCURA
    accura_items, accura_sides = test_accura_from_text(pdf_content)
    
    # Test BOERE  
    boere_items = test_boere_from_text(pdf_content)
    
    print(f"\n" + "="*50)
    print("SUMMARY:")
    print(f"ACCURA: {accura_items} items, {accura_sides} sides")
    print(f"BOERE: {boere_items} items")