// NODE.JS PDF TO SQL EXTRACTOR
// Using PDF-parse and other Node.js libraries

const fs = require('fs');
const path = require('path');

// Check if pdf-parse is available
let pdfParse;
try {
    pdfParse = require('pdf-parse');
} catch (e) {
    console.log('❌ pdf-parse not installed. Install with: npm install pdf-parse');
    process.exit(1);
}

// SQLite for SQL storage
let sqlite3;
try {
    sqlite3 = require('sqlite3').verbose();
} catch (e) {
    console.log('❌ sqlite3 not installed. Install with: npm install sqlite3');
    process.exit(1);
}

async function extractPdfToSQL(pdfPath) {
    console.log('🔍 NODE.JS PDF EXTRACTION TO SQL');
    console.log('================================');
    
    try {
        // Read PDF file
        const dataBuffer = fs.readFileSync(pdfPath);
        
        // Extract PDF content
        console.log('📄 Parsing PDF...');
        const pdfData = await pdfParse(dataBuffer, {
            // Options for better extraction
            normalizeWhitespace: false,
            disableCombineTextItems: false
        });
        
        console.log(`✅ Extracted ${pdfData.numpages} pages`);
        console.log(`✅ Total text length: ${pdfData.text.length} characters`);
        
        // Create SQLite database
        const dbPath = 'nodejs_pdf_extraction.db';
        const db = new sqlite3.Database(dbPath);
        
        // Create tables
        await createTables(db);
        
        // Process text line by line
        const lines = pdfData.text.split('\n');
        console.log(`📝 Processing ${lines.length} lines...`);
        
        // Insert text data
        const stmt = db.prepare(`
            INSERT INTO pdf_text (line_number, content, is_numbered, has_section_header)
            VALUES (?, ?, ?, ?)
        `);
        
        let nestingCount = 0;
        let numberedItems = 0;
        let sectionHeaders = 0;
        
        lines.forEach((line, index) => {
            const trimmedLine = line.trim();
            if (trimmedLine) {
                const isNumbered = /^\d+\s+\w+/.test(trimmedLine);
                const hasSectionHeader = /\b(nesting|opdeelzaag|controle|massief|magazijn)\b/i.test(trimmedLine);
                const hasAantal = /aantal onderdelen/i.test(trimmedLine);
                
                stmt.run(index + 1, trimmedLine, isNumbered ? 1 : 0, hasSectionHeader ? 1 : 0);
                
                if (isNumbered) numberedItems++;
                if (hasSectionHeader) sectionHeaders++;
                if (hasAantal) nestingCount++;
            }
        });
        
        stmt.finalize();
        
        // Extract specific data with SQL queries
        console.log('\n📊 ANALYZING EXTRACTED DATA:');
        
        // NESTING analysis
        db.all(`
            SELECT content FROM pdf_text 
            WHERE LOWER(content) LIKE '%aantal onderdelen%'
        `, (err, rows) => {
            if (err) {
                console.error('❌ NESTING query error:', err);
            } else {
                console.log(`✅ NESTING markers found: ${rows.length}`);
                rows.forEach((row, i) => {
                    const numbers = row.content.match(/\d+/g);
                    if (numbers) {
                        console.log(`   ${i+1}. Aantal onderdelen: ${numbers[numbers.length-1]}`);
                    }
                });
            }
        });
        
        // BOERE analysis
        db.all(`
            SELECT content FROM pdf_text 
            WHERE LOWER(content) LIKE '%beschrijving%' 
            AND LOWER(content) LIKE '%aantal stuks%'
        `, (err, rows) => {
            if (err) {
                console.error('❌ BOERE query error:', err);
            } else {
                console.log(`✅ BOERE table headers found: ${rows.length}`);
            }
        });
        
        // ACCURA analysis
        db.all(`
            SELECT COUNT(*) as count FROM pdf_text 
            WHERE is_numbered = 1 
            AND (LOWER(content) LIKE '%fineer%' 
                 OR LOWER(content) LIKE '%finger%' 
                 OR LOWER(content) LIKE '%l1%'
                 OR LOWER(content) LIKE '%l2%')
        `, (err, rows) => {
            if (err) {
                console.error('❌ ACCURA query error:', err);
            } else {
                console.log(`✅ ACCURA items (with edge processing): ${rows[0].count}`);
            }
        });
        
        // Summary
        setTimeout(() => {
            console.log('\n📈 EXTRACTION SUMMARY:');
            console.log(`   Total lines processed: ${lines.length}`);
            console.log(`   Numbered items: ${numberedItems}`);
            console.log(`   Section headers: ${sectionHeaders}`);
            console.log(`   "Aantal onderdelen" markers: ${nestingCount}`);
            console.log(`   SQL database: ${dbPath}`);
            
            db.close();
            console.log('\n✅ Node.js PDF to SQL extraction completed!');
        }, 1000);
        
    } catch (error) {
        console.error('❌ PDF extraction error:', error);
    }
}

function createTables(db) {
    return new Promise((resolve, reject) => {
        db.serialize(() => {
            // Create main text table
            db.run(`
                CREATE TABLE IF NOT EXISTS pdf_text (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    line_number INTEGER,
                    content TEXT,
                    is_numbered INTEGER DEFAULT 0,
                    has_section_header INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            `);
            
            // Create analysis table
            db.run(`
                CREATE TABLE IF NOT EXISTS extraction_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT,
                    metric_value INTEGER,
                    details TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            `);
            
            resolve();
        });
    });
}

// Test the extraction
const pdfFile = 'S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF';

if (fs.existsSync(pdfFile)) {
    extractPdfToSQL(pdfFile);
} else {
    console.log('❌ PDF file not found:', pdfFile);
    console.log('💡 Make sure the PDF file is in the current directory');
}