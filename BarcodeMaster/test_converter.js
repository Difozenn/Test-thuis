// Test the converter.js with your PDF text
const fs = require('fs');
const XLSX = require('xlsx');

// Load the converter functions
eval(fs.readFileSync('converter.js', 'utf8'));

// Load PDF text
const pdfText = fs.readFileSync('tv_wand_text.txt', 'utf8');

console.log('📄 PDF Text Sample:');
console.log(pdfText.substring(0, 500) + '...\n');

// Convert to Excel
console.log('🔄 Converting to Excel...');
const result = convertPDFToExcel(pdfText, 'tv_wand_converted.xlsx');

if (result.success) {
    console.log('✅ Conversion successful!');
    console.log(`📊 Found ${result.tables.length} tables`);
    console.log('📈 Metadata:', result.metadata);
    
    // Show table details
    result.tables.forEach((table, index) => {
        console.log(`\nTable ${index + 1}: ${table.name}`);
        console.log(`Headers: ${table.headers.join(', ')}`);
        console.log(`Data rows: ${table.data.length}`);
        console.log('First few rows:');
        table.data.slice(0, 3).forEach((row, i) => {
            console.log(`  Row ${i + 1}: ${row.join(' | ')}`);
        });
    });
    
    // Save Excel file
    fs.writeFileSync(result.fileName, result.buffer);
    console.log(`\n📁 Excel file saved as: ${result.fileName}`);
    
} else {
    console.error('❌ Conversion failed:', result.error);
}