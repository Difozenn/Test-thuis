// Test fixing the Fineer extraction
const fs = require('fs');
const XLSX = require('xlsx');

// Load the updated converter
eval(fs.readFileSync('converter.js', 'utf8'));

// Test with a simple PDF text that has Fineer data
const testPdfText = `
MO07202
S04479
Klant: Rudi Matterne
Tekenaar: JW

Nesting
N° Onderdeel Materiaal Lengte Breedte Dikte L1 L2 B1 B2 ProductieM. Opmerkingen
1 BC HSP 19mm BxB 493 375 19 Fineer eikFineer eik Standaard
7 BC HSP 19mm BxB 987 446 19 Fineer eikFineer eikFineer eikFineer eik Standaard
Aantal onderdelen: 2
`;

console.log('🧪 Testing Fineer extraction fix...\n');

// Override the parseProductionRowExact function to fix Fineer detection
const originalParse = parseProductionRowExact;
parseProductionRowExact = function(rowNum, parts, fullLine) {
    // Get the result from original parser
    const result = originalParse(rowNum, parts, fullLine);
    
    // Fix the Fineer extraction - look for "Fineer eik" not "Fineer eik 1mm"
    const fineerMatches = (fullLine.match(/Fineer\s+eik/g) || []);
    result.l1 = fineerMatches.length >= 1 ? 'Fineer eik 1mm' : '';
    result.l2 = fineerMatches.length >= 2 ? 'Fineer eik 1mm' : '';
    result.b1 = fineerMatches.length >= 3 ? 'Fineer eik 1mm' : '';
    result.b2 = fineerMatches.length >= 4 ? 'Fineer eik 1mm' : '';
    
    console.log(`Row ${rowNum}: Found ${fineerMatches.length} Fineer matches`);
    console.log(`  L1=${result.l1}, L2=${result.l2}, B1=${result.b1}, B2=${result.b2}`);
    
    return result;
};

// Convert with the fix
const result = convertPDFToExactExcel(testPdfText, 'test_fineer_fixed.xlsx');

if (result.success) {
    fs.writeFileSync(result.fileName, result.buffer);
    console.log('\n✅ Test file created with Fineer fix');
    
    // Verify the fix worked
    const wb = XLSX.readFile(result.fileName);
    const sheet = wb.Sheets['Table 2'];
    if (sheet) {
        console.log('\nVerifying L1/L2/B1/B2 content:');
        console.log(`K6 (L1): ${sheet['K6']?.v || 'empty'}`);
        console.log(`L6 (L2): ${sheet['L6']?.v || 'empty'}`);
        console.log(`M6 (B1): ${sheet['M6']?.v || 'empty'}`);
        console.log(`N6 (B2): ${sheet['N6']?.v || 'empty'}`);
    }
}