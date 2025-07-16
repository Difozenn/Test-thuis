// Test converter2.js with your PDF files
const fs = require('fs');
const XLSX = require('xlsx');

// Load converter2.js
eval(fs.readFileSync('converter2.js', 'utf8'));

// Load PDF text
const pdfText = fs.readFileSync('tv_wand_text.txt', 'utf8');

console.log('📄 Testing converter2.js...\n');

// Try to find which function is exported by converter2
console.log('Available functions:');
if (typeof convertPDFToExactExcel !== 'undefined') {
    console.log('  - convertPDFToExactExcel');
}
if (typeof convertPDFToExcel !== 'undefined') {
    console.log('  - convertPDFToExcel');
}
if (typeof processManufacturingPDF !== 'undefined') {
    console.log('  - processManufacturingPDF');
}

// Try different possible function names
let result;
try {
    if (typeof convertPDFToExactExcel !== 'undefined') {
        console.log('\n🔄 Using convertPDFToExactExcel...');
        result = convertPDFToExactExcel(pdfText, 'tv_wand_converter2.xlsx');
    } else if (typeof convertPDFToExcel !== 'undefined') {
        console.log('\n🔄 Using convertPDFToExcel...');
        result = convertPDFToExcel(pdfText, 'tv_wand_converter2.xlsx');
    } else if (typeof processManufacturingPDF !== 'undefined') {
        console.log('\n🔄 Using processManufacturingPDF...');
        result = processManufacturingPDF(pdfText, 'tv_wand_converter2.xlsx');
    } else {
        console.error('❌ No known conversion function found in converter2.js');
        process.exit(1);
    }
} catch (error) {
    console.error('❌ Error during conversion:', error.message);
    process.exit(1);
}

if (result && result.success) {
    console.log('✅ Conversion successful!');
    if (result.sheetsCreated) console.log(`📊 Created ${result.sheetsCreated} sheets`);
    if (result.metadata) console.log('📈 Metadata:', result.metadata);
    if (result.tables) console.log(`📊 Found ${result.tables.length} tables`);
    
    // Save Excel file
    fs.writeFileSync(result.fileName, result.buffer);
    console.log(`\n📁 Excel file saved as: ${result.fileName}`);
    console.log(`📏 File size: ${(result.buffer.length / 1024).toFixed(2)} KB`);
} else {
    console.error('❌ Conversion failed:', result?.error || 'Unknown error');
}