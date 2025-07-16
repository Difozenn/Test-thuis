import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.ss.util.CellRangeAddress;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import technology.tabula.*;
import technology.tabula.extractors.SpreadsheetExtractionAlgorithm;

import java.io.*;
import java.util.*;
import java.util.regex.*;

public class PDFToExcelConverter {
    
    private static class ProjectMetadata {
        String projectCode = "";
        String salesNumber = "";
        String projectName = "";
        String client = "";
        String designer = "";
        String department = "";
    }
    
    private static class TableSection {
        String type;
        List<String> headers = new ArrayList<>();
        List<Map<String, String>> data = new ArrayList<>();
        int totalItems = 0;
    }
    
    public static void main(String[] args) {
        if (args.length < 1) {
            // Default files for testing
            convertPDF("S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF", 
                      "hoekdressing_java_converted.xlsx");
            convertPDF("S04479_RAPPORT_Rudi Matterne_0411_MO07202-7203_TV-wand (7-7).PDF", 
                      "tv_wand_java_converted.xlsx");
        } else {
            String inputPdf = args[0];
            String outputExcel = args.length > 1 ? args[1] : inputPdf.replace(".pdf", "_converted.xlsx").replace(".PDF", "_converted.xlsx");
            convertPDF(inputPdf, outputExcel);
        }
    }
    
    public static void convertPDF(String pdfPath, String excelPath) {
        System.out.println("🔄 Converting " + pdfPath + "...");
        
        try {
            // Extract metadata and text
            ProjectMetadata metadata = extractMetadata(pdfPath);
            
            // Extract tables using Tabula
            List<TableSection> sections = extractTablesWithTabula(pdfPath);
            
            // Fallback to text extraction if Tabula fails
            if (sections.isEmpty()) {
                System.out.println("⚠️  Tabula extraction failed, using PDFBox text extraction...");
                sections = extractTablesFromText(pdfPath);
            }
            
            // Create Excel workbook
            createExcelWorkbook(metadata, sections, excelPath);
            
            System.out.println("✅ Excel file created: " + excelPath);
            
        } catch (Exception e) {
            System.err.println("❌ Error: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    private static ProjectMetadata extractMetadata(String pdfPath) throws IOException {
        ProjectMetadata metadata = new ProjectMetadata();
        
        try (PDDocument document = PDDocument.load(new File(pdfPath))) {
            PDFTextStripper stripper = new PDFTextStripper();
            stripper.setEndPage(1); // First page only
            String text = stripper.getText(document);
            
            // Extract patterns
            Pattern moPattern = Pattern.compile("(MO\\d+(?:-\\d+)?)");
            Pattern sPattern = Pattern.compile("(S\\d+)");
            Pattern projectPattern = Pattern.compile("0411_MO\\d+[-\\d]*_([^\\n]+?)\\s*\\(");
            Pattern clientPattern = Pattern.compile("(?:Klant:|Client:)\\s*([A-Za-z\\s]+?)(?:\\n|Tekenaar|JW)");
            Pattern designerPattern = Pattern.compile("(?:Tekenaar:|Designer:)\\s*([A-Z]+)");
            
            Matcher m;
            
            m = moPattern.matcher(text);
            if (m.find()) metadata.projectCode = m.group(1);
            
            m = sPattern.matcher(text);
            if (m.find()) {
                metadata.salesNumber = m.group(1);
                metadata.department = m.group(1);
            }
            
            m = projectPattern.matcher(text);
            if (m.find()) metadata.projectName = m.group(1).trim();
            
            m = clientPattern.matcher(text);
            if (m.find()) metadata.client = m.group(1).trim();
            
            m = designerPattern.matcher(text);
            if (m.find()) {
                metadata.designer = m.group(1);
            } else if (text.contains("JW")) {
                metadata.designer = "JW";
            }
        }
        
        return metadata;
    }
    
    private static List<TableSection> extractTablesWithTabula(String pdfPath) {
        List<TableSection> sections = new ArrayList<>();
        
        try (PDDocument document = PDDocument.load(new File(pdfPath))) {
            ObjectExtractor extractor = new ObjectExtractor(document);
            SpreadsheetExtractionAlgorithm algorithm = new SpreadsheetExtractionAlgorithm();
            
            for (int pageNum = 1; pageNum <= document.getNumberOfPages(); pageNum++) {
                Page page = extractor.extract(pageNum);
                
                for (Table table : algorithm.extract(page)) {
                    TableSection section = processTable(table, page.getText());
                    if (section != null && !section.data.isEmpty()) {
                        sections.add(section);
                    }
                }
            }
        } catch (Exception e) {
            System.err.println("Tabula extraction error: " + e.getMessage());
        }
        
        return sections;
    }
    
    private static TableSection processTable(Table table, String pageText) {
        if (table.getRowCount() < 2) return null;
        
        TableSection section = new TableSection();
        
        // Determine table type from context
        String textLower = pageText.toLowerCase();
        if (textLower.contains("nesting")) {
            section.type = "nesting";
        } else if (textLower.contains("opdeelzaag")) {
            section.type = "opdeelzaag";
        } else if (textLower.contains("magazijn")) {
            section.type = "magazijn";
        } else if (textLower.contains("massief")) {
            section.type = "massief";
        } else {
            section.type = "unknown";
        }
        
        // Extract headers from first row
        List<RectangularTextContainer> headerRow = table.getRow(0);
        for (RectangularTextContainer cell : headerRow) {
            String header = cell.getText().trim();
            if (!header.isEmpty()) {
                section.headers.add(header);
            }
        }
        
        // Process data rows
        for (int i = 1; i < table.getRowCount(); i++) {
            List<RectangularTextContainer> row = table.getRow(i);
            Map<String, String> rowData = new HashMap<>();
            
            // Check if this is a numbered row
            if (row.size() > 0) {
                String firstCell = row.get(0).getText().trim();
                if (firstCell.matches("\\d+")) {
                    // Process the row based on section type
                    if (section.type.equals("nesting") || section.type.equals("opdeelzaag")) {
                        rowData = processProductionRow(row, table.getRow(Math.min(i + 1, table.getRowCount() - 1)));
                    } else if (section.type.equals("magazijn")) {
                        rowData = processMagazijnRow(row);
                    }
                    
                    if (!rowData.isEmpty()) {
                        section.data.add(rowData);
                    }
                }
            }
        }
        
        section.totalItems = section.data.size();
        return section;
    }
    
    private static Map<String, String> processProductionRow(List<RectangularTextContainer> row, 
                                                           List<RectangularTextContainer> nextRow) {
        Map<String, String> data = new HashMap<>();
        
        if (row.size() < 6) return data;
        
        data.put("N°", row.get(0).getText().trim());
        data.put("Onderdeel", row.size() > 1 ? row.get(1).getText().trim() : "");
        data.put("Materiaal", row.size() > 2 ? row.get(2).getText().trim() : "");
        data.put("Lengte", row.size() > 3 ? row.get(3).getText().trim() : "");
        data.put("Breedte", row.size() > 4 ? row.get(4).getText().trim() : "");
        data.put("Dikte", row.size() > 5 ? row.get(5).getText().trim() : "");
        
        // Extract L1/L2/B1/B2 from current and next row
        StringBuilder fullText = new StringBuilder();
        for (RectangularTextContainer cell : row) {
            fullText.append(cell.getText()).append(" ");
        }
        for (RectangularTextContainer cell : nextRow) {
            fullText.append(cell.getText()).append(" ");
        }
        
        String combined = fullText.toString();
        int fineerCount = countOccurrences(combined, "Fineer\\s*eik");
        
        data.put("L1", fineerCount >= 1 ? "Fineer eik 1mm" : "");
        data.put("L2", fineerCount >= 2 ? "Fineer eik 1mm" : "");
        data.put("B1", fineerCount >= 3 ? "Fineer eik 1mm" : "");
        data.put("B2", fineerCount >= 4 ? "Fineer eik 1mm" : "");
        
        // Extract ProductieM
        if (combined.contains("Standaard")) {
            String productieM = "Standaard";
            if (combined.contains("Dik")) {
                productieM += " Dik";
            }
            data.put("ProductieM.", productieM);
        }
        
        // Extract Opmerkingen
        List<String> remarks = new ArrayList<>();
        Pattern overmaat = Pattern.compile("([LB+]=\\d+mm overmaat|[\\w\\s]*\\d+mm overmaat)");
        Matcher m = overmaat.matcher(combined);
        while (m.find()) {
            remarks.add(m.group(1));
        }
        
        if (combined.toLowerCase().contains("frezen")) {
            Pattern frezen = Pattern.compile("([\\w\\s]*frezen[\\w\\s,]*)", Pattern.CASE_INSENSITIVE);
            m = frezen.matcher(combined);
            if (m.find()) {
                remarks.add(m.group(1));
            }
        }
        
        data.put("Opmerkingen", String.join(", ", remarks));
        
        return data;
    }
    
    private static Map<String, String> processMagazijnRow(List<RectangularTextContainer> row) {
        Map<String, String> data = new HashMap<>();
        
        data.put("N°", row.get(0).getText().trim());
        
        if (row.size() >= 4) {
            data.put("Beschrijving", row.get(1).getText().trim());
            data.put("Aantal stuks", row.get(2).getText().trim());
            data.put("GB nummer", row.get(3).getText().trim());
        } else if (row.size() >= 3) {
            // Concatenate description parts
            StringBuilder desc = new StringBuilder();
            for (int i = 1; i < row.size() - 2; i++) {
                desc.append(row.get(i).getText()).append(" ");
            }
            data.put("Beschrijving", desc.toString().trim());
            data.put("Aantal stuks", row.get(row.size() - 2).getText().trim());
            data.put("GB nummer", row.get(row.size() - 1).getText().trim());
        }
        
        return data;
    }
    
    private static List<TableSection> extractTablesFromText(String pdfPath) throws IOException {
        List<TableSection> sections = new ArrayList<>();
        
        try (PDDocument document = PDDocument.load(new File(pdfPath))) {
            PDFTextStripper stripper = new PDFTextStripper();
            String fullText = stripper.getText(document);
            
            String[] lines = fullText.split("\n");
            TableSection currentSection = null;
            
            for (int i = 0; i < lines.length; i++) {
                String line = lines[i].trim();
                String lineLower = line.toLowerCase();
                
                // Check for section headers
                if (lineLower.contains("nesting") || lineLower.contains("opdeelzaag") || 
                    lineLower.contains("magazijn") || lineLower.contains("massief")) {
                    
                    if (currentSection != null && !currentSection.data.isEmpty()) {
                        sections.add(currentSection);
                    }
                    
                    currentSection = new TableSection();
                    if (lineLower.contains("nesting")) currentSection.type = "nesting";
                    else if (lineLower.contains("opdeelzaag")) currentSection.type = "opdeelzaag";
                    else if (lineLower.contains("magazijn")) currentSection.type = "magazijn";
                    else if (lineLower.contains("massief")) currentSection.type = "massief";
                }
                
                // Look for headers
                if (currentSection != null && line.contains("N°") && currentSection.headers.isEmpty()) {
                    currentSection.headers = parseHeaders(line, currentSection.type);
                }
                
                // Parse data rows
                if (currentSection != null && !currentSection.headers.isEmpty() && line.matches("^\\s*\\d+\\s+.*")) {
                    Map<String, String> rowData = parseDataRow(line, currentSection.type, lines, i);
                    if (!rowData.isEmpty()) {
                        currentSection.data.add(rowData);
                    }
                }
                
                // Check for section end
                if (line.contains("Aantal onderdelen:")) {
                    Pattern p = Pattern.compile("Aantal onderdelen:\\s*(\\d+)");
                    Matcher m = p.matcher(line);
                    if (m.find() && currentSection != null) {
                        currentSection.totalItems = Integer.parseInt(m.group(1));
                        sections.add(currentSection);
                        currentSection = null;
                    }
                }
            }
            
            if (currentSection != null && !currentSection.data.isEmpty()) {
                sections.add(currentSection);
            }
        }
        
        return sections;
    }
    
    private static List<String> parseHeaders(String line, String sectionType) {
        if (sectionType.equals("magazijn")) {
            return Arrays.asList("N°", "Beschrijving", "Aantal stuks", "GB nummer");
        } else if (sectionType.equals("nesting") || sectionType.equals("opdeelzaag")) {
            return Arrays.asList("N°", "Onderdeel", "Materiaal", "Lengte", "Breedte", 
                               "Dikte", "L1", "L2", "B1", "B2", "ProductieM.", "Opmerkingen");
        } else {
            return Arrays.asList("N°", "Onderdeel", "Materiaal", "Lengte", "Breedte", "Dikte", "Opmerkingen");
        }
    }
    
    private static Map<String, String> parseDataRow(String line, String sectionType, String[] allLines, int lineIdx) {
        Map<String, String> data = new HashMap<>();
        
        // Get full line content including next line if it contains "1mm"
        String fullLine = line;
        if (lineIdx + 1 < allLines.length && allLines[lineIdx + 1].contains("1mm")) {
            fullLine += " " + allLines[lineIdx + 1];
        }
        
        Pattern p = Pattern.compile("^\\s*(\\d+)\\s+(.+)$");
        Matcher m = p.matcher(line);
        if (!m.find()) return data;
        
        data.put("N°", m.group(1));
        String rest = m.group(2);
        
        if (sectionType.equals("nesting") || sectionType.equals("opdeelzaag")) {
            return parseProductionTextRow(data.get("N°"), rest, fullLine);
        } else if (sectionType.equals("magazijn")) {
            return parseMagazijnTextRow(data.get("N°"), rest);
        }
        
        return data;
    }
    
    private static Map<String, String> parseProductionTextRow(String rowNum, String rest, String fullLine) {
        Map<String, String> data = new HashMap<>();
        data.put("N°", rowNum);
        
        String[] parts = rest.split("\\s+");
        int idx = 0;
        
        // Onderdeel
        data.put("Onderdeel", idx < parts.length ? parts[idx++] : "");
        
        // Material (collect until number)
        StringBuilder material = new StringBuilder();
        while (idx < parts.length && !parts[idx].matches("\\d+\\.?\\d*")) {
            material.append(parts[idx++]).append(" ");
        }
        data.put("Materiaal", material.toString().trim());
        
        // Dimensions
        data.put("Lengte", idx < parts.length ? parts[idx++] : "");
        data.put("Breedte", idx < parts.length ? parts[idx++] : "");
        data.put("Dikte", idx < parts.length ? parts[idx++] : "");
        
        // Count Fineer occurrences
        int fineerCount = countOccurrences(fullLine, "Fineer\\s*eik");
        
        data.put("L1", fineerCount >= 1 ? "Fineer eik 1mm" : "");
        data.put("L2", fineerCount >= 2 ? "Fineer eik 1mm" : "");
        data.put("B1", fineerCount >= 3 ? "Fineer eik 1mm" : "");
        data.put("B2", fineerCount >= 4 ? "Fineer eik 1mm" : "");
        
        // ProductieM
        if (fullLine.contains("Standaard")) {
            String productieM = "Standaard";
            if (fullLine.contains("Dik")) {
                productieM += " Dik";
            }
            data.put("ProductieM.", productieM);
        } else {
            data.put("ProductieM.", "");
        }
        
        // Opmerkingen
        List<String> remarks = new ArrayList<>();
        if (fullLine.contains("overmaat")) {
            Pattern overmaat = Pattern.compile("([LB+]=\\d+mm overmaat|[\\w\\s]*\\d+mm overmaat)");
            Matcher m = overmaat.matcher(fullLine);
            while (m.find()) {
                remarks.add(m.group(1));
            }
        }
        data.put("Opmerkingen", String.join(", ", remarks));
        
        return data;
    }
    
    private static Map<String, String> parseMagazijnTextRow(String rowNum, String rest) {
        Map<String, String> data = new HashMap<>();
        data.put("N°", rowNum);
        
        Pattern p = Pattern.compile("^(.+?)\\s+(\\d+)\\s*(.*)$");
        Matcher m = p.matcher(rest);
        
        if (m.find()) {
            data.put("Beschrijving", m.group(1).trim());
            data.put("Aantal stuks", m.group(2));
            data.put("GB nummer", m.group(3).trim());
        } else {
            data.put("Beschrijving", rest);
            data.put("Aantal stuks", "");
            data.put("GB nummer", "");
        }
        
        return data;
    }
    
    private static int countOccurrences(String text, String pattern) {
        Pattern p = Pattern.compile(pattern);
        Matcher m = p.matcher(text);
        int count = 0;
        while (m.find()) {
            count++;
        }
        return count;
    }
    
    private static void createExcelWorkbook(ProjectMetadata metadata, List<TableSection> sections, 
                                           String outputPath) throws IOException {
        Workbook workbook = new XSSFWorkbook();
        
        // Create cover sheet
        createCoverSheet(workbook, metadata);
        
        // Create data sheets
        int sheetNum = 2;
        for (TableSection section : sections) {
            createDataSheet(workbook, section, metadata, sheetNum++);
        }
        
        // Write to file
        try (FileOutputStream out = new FileOutputStream(outputPath)) {
            workbook.write(out);
        }
        workbook.close();
    }
    
    private static void createCoverSheet(Workbook workbook, ProjectMetadata metadata) {
        Sheet sheet = workbook.createSheet("Table 1");
        
        // Create content
        createCell(sheet, 0, 0, "Project:\nKlant:\nTekenaar:");
        createCell(sheet, 0, 3, metadata.projectCode + "\n" + metadata.salesNumber + "\n" + 
                               metadata.projectName + " " + metadata.client + "\n" + metadata.designer);
        createCell(sheet, 1, 0, metadata.department);
        createCell(sheet, 2, 0, "info:\nSchuren");
        createCell(sheet, 3, 0, "Totaal aantal onderdelen:");
        createCell(sheet, 4, 0, "Afwerking: Lakstraat");
        createCell(sheet, 5, 0, "Enkel als aangevinkt.                  Handwerk voor het schuren.\n" +
                               "Kasten monteren! onderdelen sorteren per object Vlakstraat: gekleurde sjang gebruiken.");
        createCell(sheet, 6, 0, "Datum:");
        createCell(sheet, 6, 1, "kopie: terugbezorgen na schuren!");
        
        // Signature sections
        String[] sections = {"Cel Holzer:", "Accura:", "Reichenbacher:", "Kl Gannomat:", "Cel Massief:", "Cel schuren:"};
        for (int i = 0; i < sections.length; i++) {
            createCell(sheet, 7 + i, 0, sections[i] + "\nNaam:                          .../...");
        }
        
        createCell(sheet, 7, 2, "Opmerkingen:");
        
        // Apply merges
        sheet.addMergedRegion(new CellRangeAddress(0, 0, 0, 2));
        sheet.addMergedRegion(new CellRangeAddress(0, 0, 3, 5));
        sheet.addMergedRegion(new CellRangeAddress(1, 1, 0, 1));
        sheet.addMergedRegion(new CellRangeAddress(2, 2, 0, 1));
        sheet.addMergedRegion(new CellRangeAddress(3, 3, 0, 1));
        sheet.addMergedRegion(new CellRangeAddress(4, 4, 0, 5));
        sheet.addMergedRegion(new CellRangeAddress(5, 5, 0, 3));
        sheet.addMergedRegion(new CellRangeAddress(6, 6, 1, 5));
        sheet.addMergedRegion(new CellRangeAddress(7, 12, 2, 4));
        
        // Set column widths
        sheet.setColumnWidth(0, 9651); // 37.56 * 256
        sheet.setColumnWidth(1, 512);
        sheet.setColumnWidth(2, 2959);
        sheet.setColumnWidth(3, 8135);
        sheet.setColumnWidth(4, 10809);
        sheet.setColumnWidth(5, 740);
    }
    
    private static void createDataSheet(Workbook workbook, TableSection section, 
                                       ProjectMetadata metadata, int sheetNum) {
        Sheet sheet = workbook.createSheet("Table " + sheetNum);
        
        // Header section
        createCell(sheet, 0, 0, metadata.department);
        createCell(sheet, 1, 0, "Klant:");
        createCell(sheet, 1, 6, metadata.client);
        createCell(sheet, 1, 14, metadata.projectCode);
        createCell(sheet, 2, 0, "Tekenaar:  " + metadata.designer + "\nSales nr:    " + metadata.salesNumber);
        createCell(sheet, 3, 0, "Schuren");
        createCell(sheet, 3, 4, "Project:");
        createCell(sheet, 3, 7, metadata.projectName + "                                                       " + 
                               section.type.substring(0, 1).toUpperCase() + section.type.substring(1));
        
        // Column headers
        Row headerRow = sheet.createRow(4);
        if (section.type.equals("nesting") || section.type.equals("opdeelzaag")) {
            createCell(sheet, 4, 0, "N°");
            createCell(sheet, 4, 1, "Onderdeel");
            createCell(sheet, 4, 3, "Materiaal");
            createCell(sheet, 4, 5, "Lengte");
            createCell(sheet, 4, 8, "Breedte");
            createCell(sheet, 4, 9, "Dikte");
            createCell(sheet, 4, 10, "L1");
            createCell(sheet, 4, 11, "L2");
            createCell(sheet, 4, 12, "B1");
            createCell(sheet, 4, 13, "B2");
            if (section.type.equals("nesting")) {
                createCell(sheet, 4, 15, "ProductieM.");
                createCell(sheet, 4, 16, "Opmerkingen");
            } else {
                createCell(sheet, 4, 15, "Opmerkingen");
            }
        } else if (section.type.equals("magazijn")) {
            createCell(sheet, 4, 0, "N°");
            createCell(sheet, 4, 1, "Beschrijving");
            createCell(sheet, 4, 8, "Aantal stuks");
            createCell(sheet, 4, 15, "GB nummer");
        }
        
        // Data rows
        int rowNum = 5;
        for (Map<String, String> rowData : section.data) {
            if (section.type.equals("nesting") || section.type.equals("opdeelzaag")) {
                createCell(sheet, rowNum, 0, rowData.getOrDefault("N°", ""));
                createCell(sheet, rowNum, 1, rowData.getOrDefault("Onderdeel", ""));
                createCell(sheet, rowNum, 3, rowData.getOrDefault("Materiaal", ""));
                createCell(sheet, rowNum, 5, rowData.getOrDefault("Lengte", ""));
                createCell(sheet, rowNum, 8, rowData.getOrDefault("Breedte", ""));
                createCell(sheet, rowNum, 9, rowData.getOrDefault("Dikte", ""));
                createCell(sheet, rowNum, 10, rowData.getOrDefault("L1", ""));
                createCell(sheet, rowNum, 11, rowData.getOrDefault("L2", ""));
                createCell(sheet, rowNum, 12, rowData.getOrDefault("B1", ""));
                createCell(sheet, rowNum, 13, rowData.getOrDefault("B2", ""));
                if (section.type.equals("nesting")) {
                    createCell(sheet, rowNum, 15, rowData.getOrDefault("ProductieM.", ""));
                    createCell(sheet, rowNum, 16, rowData.getOrDefault("Opmerkingen", ""));
                } else {
                    createCell(sheet, rowNum, 15, rowData.getOrDefault("Opmerkingen", ""));
                }
            } else if (section.type.equals("magazijn")) {
                createCell(sheet, rowNum, 0, rowData.getOrDefault("N°", ""));
                createCell(sheet, rowNum, 1, rowData.getOrDefault("Beschrijving", ""));
                createCell(sheet, rowNum, 8, rowData.getOrDefault("Aantal stuks", ""));
                createCell(sheet, rowNum, 15, rowData.getOrDefault("GB nummer", ""));
            }
            rowNum++;
        }
        
        // Total row
        createCell(sheet, rowNum, 0, "Aantal onderdelen: " + section.totalItems);
        
        // Apply merges
        applyDataSheetMerges(sheet, section.data.size());
        
        // Set column widths
        setDataSheetColumnWidths(sheet);
    }
    
    private static void applyDataSheetMerges(Sheet sheet, int dataRowCount) {
        // Header merges
        sheet.addMergedRegion(new CellRangeAddress(0, 0, 0, 1));
        sheet.addMergedRegion(new CellRangeAddress(1, 1, 0, 5));
        sheet.addMergedRegion(new CellRangeAddress(1, 1, 6, 13));
        sheet.addMergedRegion(new CellRangeAddress(1, 1, 14, 17));
        sheet.addMergedRegion(new CellRangeAddress(2, 2, 0, 17));
        sheet.addMergedRegion(new CellRangeAddress(3, 3, 0, 3));
        sheet.addMergedRegion(new CellRangeAddress(3, 3, 4, 6));
        sheet.addMergedRegion(new CellRangeAddress(3, 3, 7, 17));
        
        // Column header merges
        sheet.addMergedRegion(new CellRangeAddress(4, 4, 1, 2));
        sheet.addMergedRegion(new CellRangeAddress(4, 4, 3, 4));
        sheet.addMergedRegion(new CellRangeAddress(4, 4, 5, 7));
        sheet.addMergedRegion(new CellRangeAddress(4, 4, 13, 14));
        
        // Data row merges
        for (int i = 5; i < 5 + dataRowCount; i++) {
            sheet.addMergedRegion(new CellRangeAddress(i, i, 1, 2));
            sheet.addMergedRegion(new CellRangeAddress(i, i, 3, 4));
            sheet.addMergedRegion(new CellRangeAddress(i, i, 5, 7));
            sheet.addMergedRegion(new CellRangeAddress(i, i, 13, 14));
        }
        
        // Total row merge
        sheet.addMergedRegion(new CellRangeAddress(5 + dataRowCount, 5 + dataRowCount, 0, 17));
    }
    
    private static void setDataSheetColumnWidths(Sheet sheet) {
        sheet.setColumnWidth(0, 1308);  // 5.11 * 256
        sheet.setColumnWidth(1, 2389);  // 9.33 * 256
        sheet.setColumnWidth(2, 3698);  // 14.44 * 256
        sheet.setColumnWidth(3, 6769);  // 26.44 * 256
        sheet.setColumnWidth(4, 626);   // 2.44 * 256
        sheet.setColumnWidth(5, 1877);  // 7.33 * 256
        sheet.setColumnWidth(6, 171);   // 0.67 * 256
        sheet.setColumnWidth(7, 1308);  // 5.11 * 256
        sheet.setColumnWidth(8, 3015);  // 11.78 * 256
        sheet.setColumnWidth(9, 1991);  // 7.78 * 256
        sheet.setColumnWidth(10, 1649); // 6.44 * 256
        sheet.setColumnWidth(11, 1649); // 6.44 * 256
        sheet.setColumnWidth(12, 1707); // 6.67 * 256
        sheet.setColumnWidth(13, 796);  // 3.11 * 256
        sheet.setColumnWidth(14, 796);  // 3.11 * 256
        sheet.setColumnWidth(15, 1991); // 7.78 * 256
        sheet.setColumnWidth(16, 14734); // 57.56 * 256
        sheet.setColumnWidth(17, 796);  // 3.11 * 256
    }
    
    private static void createCell(Sheet sheet, int rowNum, int colNum, String value) {
        Row row = sheet.getRow(rowNum);
        if (row == null) {
            row = sheet.createRow(rowNum);
        }
        Cell cell = row.createCell(colNum);
        cell.setCellValue(value);
        
        // Enable text wrapping for multi-line cells
        if (value.contains("\n")) {
            CellStyle style = sheet.getWorkbook().createCellStyle();
            style.setWrapText(true);
            cell.setCellStyle(style);
        }
    }
}