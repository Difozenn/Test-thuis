// Debug the L1/L2/B1/B2 extraction
const fs = require('fs');

// Simple test of the parsing logic
const testLines = [
    "1 BC HSP 19mm BxB 493 375 19 Fineer eikFineer eik Standaard",
    "7 BC HSP 19mm BxB 987 446 19 Fineer eikFineer eikFineer eikFineer eik Standaard",
    "18 LZ HSP 19mm BxB 564 376 19 Fineer eikFineer eikFineer eikFineer eik Standaard Hoeken recht frezen"
];

console.log('Testing L1/L2/B1/B2 extraction:\n');

testLines.forEach(line => {
    console.log(`\nLine: ${line}`);
    
    // Count "Fineer eik" occurrences
    const fineerMatches = line.match(/Fineer eik/g) || [];
    console.log(`Found ${fineerMatches.length} "Fineer eik" occurrences`);
    
    // Try to extract the fineer section
    const parts = line.split(/\s+/);
    
    // Find where dimensions end (after 3 numbers)
    let dimCount = 0;
    let fineerStartIdx = -1;
    for (let i = 2; i < parts.length; i++) { // Skip N° and Onderdeel
        if (/^\d+\.?\d*$/.test(parts[i])) {
            dimCount++;
            if (dimCount === 3) { // After Lengte, Breedte, Dikte
                fineerStartIdx = i + 1;
                break;
            }
        }
    }
    
    console.log(`Fineer section starts at index: ${fineerStartIdx}`);
    
    if (fineerStartIdx > 0) {
        // Extract everything between dimensions and "Standaard"
        let fineerSection = '';
        for (let i = fineerStartIdx; i < parts.length; i++) {
            if (parts[i] === 'Standaard') break;
            fineerSection += parts[i] + ' ';
        }
        
        console.log(`Fineer section: "${fineerSection.trim()}"`);
        
        // Parse individual Fineer eik entries
        const fineerPattern = /Fineer\s+eik/g;
        const matches = [];
        let match;
        while ((match = fineerPattern.exec(fineerSection)) !== null) {
            matches.push('Fineer eik 1mm');
        }
        
        console.log('L1:', matches[0] || '');
        console.log('L2:', matches[1] || '');
        console.log('B1:', matches[2] || '');
        console.log('B2:', matches[3] || '');
    }
});