// Test the exact structure converter with your PDF text
const fs = require('fs');
const XLSX = require('xlsx');

// Load the new converter functions
eval(fs.readFileSync('converter.js', 'utf8'));

// Load PDF text
const pdfText = fs.readFileSync('tv_wand_text.txt', 'utf8');

console.log('📄 Testing EXACT STRUCTURE converter...\n');

// Convert to Excel with exact structure
console.log('🔄 Converting with exact cell layout and merges...');
const result = convertPDFToExactExcel(pdfText, 'tv_wand_exact_structure.xlsx');

if (result.success) {
    console.log('✅ Conversion successful!');
    console.log(`📊 Created ${result.sheetsCreated} sheets`);
    console.log('📈 Metadata extracted:', result.metadata);
    
    // Save Excel file
    fs.writeFileSync(result.fileName, result.buffer);
    console.log(`\n📁 Excel file saved as: ${result.fileName}`);
    console.log(`📏 File size: ${(result.buffer.length / 1024).toFixed(2)} KB`);
    
    // Also test with the Hoekdressing PDF
    console.log('\n\n🔄 Testing with Hoekdressing PDF...');
    
    // Extract text from Hoekdressing PDF
    const { execSync } = require('child_process');
    execSync(`python3 -c "
import pdfplumber
with pdfplumber.open('S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF') as pdf:
    text = ''
    for page in pdf.pages:
        if page.extract_text():
            text += page.extract_text() + '\\n'
print(text)
" > hoekdressing_text.txt`);
    
    const hoekdressingText = fs.readFileSync('hoekdressing_text.txt', 'utf8');
    const result2 = convertPDFToExactExcel(hoekdressingText, 'hoekdressing_exact_structure.xlsx');
    
    if (result2.success) {
        fs.writeFileSync(result2.fileName, result2.buffer);
        console.log('✅ Hoekdressing conversion successful!');
        console.log(`📊 Created ${result2.sheetsCreated} sheets`);
        console.log('📈 Metadata:', result2.metadata);
        console.log(`📁 Saved as: ${result2.fileName}`);
    }
    
} else {
    console.error('❌ Conversion failed:', result.error);
}