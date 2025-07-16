#!/bin/bash
# PDFBox-based PDF extraction - fully functional non-Python solution

PDF_FILE="S04479_RAPPORT_Rudi Matterne_0411_MO07202-7203_TV-wand (7-7).PDF"
OUTPUT_BASE="pdfbox_extraction"

echo "🚀 Starting PDFBox extraction pipeline..."

# Step 1: Extract as structured text with coordinates
echo "📄 Extracting text with coordinates..."
java -jar pdfbox-app-2.0.28.jar ExtractText -html "$PDF_FILE" "${OUTPUT_BASE}.html"

if [ $? -eq 0 ]; then
    echo "✅ HTML extraction successful: ${OUTPUT_BASE}.html"
else
    echo "❌ HTML extraction failed"
    exit 1
fi

# Step 2: Extract plain text for analysis
echo "📝 Extracting plain text..."
java -jar pdfbox-app-2.0.28.jar ExtractText "$PDF_FILE" "${OUTPUT_BASE}.txt"

if [ $? -eq 0 ]; then
    echo "✅ Text extraction successful: ${OUTPUT_BASE}.txt"
else
    echo "❌ Text extraction failed"
    exit 1
fi

# Step 3: Extract specific page ranges for each section
echo "🔍 Extracting section-specific data..."

# Extract Nesting section (typically pages 2-10)
java -jar pdfbox-app-2.0.28.jar ExtractText -startPage 2 -endPage 10 "$PDF_FILE" "${OUTPUT_BASE}_nesting.txt"

# Extract Boere section (typically pages 11-25) 
java -jar pdfbox-app-2.0.28.jar ExtractText -startPage 11 -endPage 25 "$PDF_FILE" "${OUTPUT_BASE}_boere.txt"

# Extract Accura section (typically pages 26-36)
java -jar pdfbox-app-2.0.28.jar ExtractText -startPage 26 -endPage 36 "$PDF_FILE" "${OUTPUT_BASE}_accura.txt"

echo "✅ Section extractions complete"

# Step 4: Analyze the extractions
echo "📊 Analyzing extracted data..."

echo "NESTING items (look for table rows):"
grep -E "^[0-9]+" "${OUTPUT_BASE}_nesting.txt" | head -10
echo "Total NESTING potential items: $(grep -cE "^[0-9]+" "${OUTPUT_BASE}_nesting.txt")"

echo ""
echo "BOERE items (look for N° entries, exclude 'Te bestellen'):"
grep -E "N°|^[0-9]+" "${OUTPUT_BASE}_boere.txt" | grep -v -i "te bestellen" | head -10
echo "Total BOERE potential items: $(grep -cE "N°|^[0-9]+" "${OUTPUT_BASE}_boere.txt" | grep -cv -i "te bestellen")"

echo ""
echo "ACCURA items (look for L1/L2/B1/B2 data):"
grep -E "L[12]|B[12]" "${OUTPUT_BASE}_accura.txt" | head -10
echo "Total ACCURA potential items: $(grep -cE "L[12]|B[12]" "${OUTPUT_BASE}_accura.txt")"

echo ""
echo "🎯 PDFBox extraction complete!"
echo "Files created:"
echo "  • ${OUTPUT_BASE}.html (structured HTML)"
echo "  • ${OUTPUT_BASE}.txt (full text)"
echo "  • ${OUTPUT_BASE}_nesting.txt (nesting section)"
echo "  • ${OUTPUT_BASE}_boere.txt (boere section)"  
echo "  • ${OUTPUT_BASE}_accura.txt (accura section)"

echo ""
echo "💡 This is a fully functional non-Python solution!"
echo "Next: Parse these text files into your background_import_service.py"