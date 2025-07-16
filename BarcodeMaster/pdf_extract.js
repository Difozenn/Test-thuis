
const fs = require('fs');
const pdfjsLib = require('pdfjs-dist/legacy/build/pdf.js');

async function extractPDF() {
    const data = new Uint8Array(fs.readFileSync(process.argv[2]));
    const pdf = await pdfjsLib.getDocument({data}).promise;
    
    let allText = [];
    
    for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const textContent = await page.getTextContent();
        
        let pageText = textContent.items.map(item => ({
            text: item.str,
            x: item.transform[4],
            y: item.transform[5],
            width: item.width,
            height: item.height
        }));
        
        allText.push({page: i, content: pageText});
    }
    
    console.log(JSON.stringify(allText, null, 2));
}

extractPDF().catch(console.error);
        