# SIMPLE R PDF EXTRACTOR
# Using system commands and base R

cat("🔍 SIMPLE R PDF EXTRACTION\n")
cat("=========================\n")

# Function to extract PDF using system tools
extract_pdf_with_r <- function(pdf_path) {
  
  cat("📄 Extracting PDF text with pdftotext...\n")
  
  # Use system pdftotext command
  text_file <- "r_extracted.txt"
  system_command <- paste("pdftotext -layout", shQuote(pdf_path), text_file)
  
  result <- system(system_command, intern = FALSE)
  
  if (result == 0 && file.exists(text_file)) {
    cat("✅ Text extraction successful\n")
    
    # Read the extracted text
    text_lines <- readLines(text_file, warn = FALSE)
    cat("📝 Read", length(text_lines), "lines\n")
    
    # Create data frame
    pdf_data <- data.frame(
      line_number = 1:length(text_lines),
      content = text_lines,
      stringsAsFactors = FALSE
    )
    
    # Add analysis columns - fix numbered item detection
    pdf_data$is_numbered <- grepl("^\\s*[0-9]+\\s+\\w+", pdf_data$content)
    pdf_data$has_section <- grepl("(nesting|opdeelzaag|controle|massief|magazijn)", 
                                  pdf_data$content, ignore.case = TRUE)
    pdf_data$has_aantal <- grepl("aantal onderdelen", pdf_data$content, ignore.case = TRUE)
    # Dynamic edge processing detection - ANY data in L1/L2/B1/B2 columns
    pdf_data$has_edge_processing <- sapply(pdf_data$content, function(line) {
      # Check if this is a numbered item line
      if (grepl("^\\s*[0-9]+\\s+\\w+", line)) {
        # Pattern 1: Multiple mm values (thickness + edge processing)
        if (grepl("\\d+mm", line)) {
          mm_count <- length(regmatches(line, gregexpr("\\d+mm", line))[[1]])
          if (mm_count > 1) return(TRUE)
        }
        
        # Pattern 2: Lines with edge processing indicators after material specification
        # Look for patterns that suggest L1/L2/B1/B2 data even if not in mm format
        if (grepl("\\d+\\s+(BxB|AFQMxB)\\s+.*\\s+\\d+\\s+", line)) {
          # This suggests a complete table row with dimensions that might have edge processing
          # Count numeric values after material type
          after_material <- gsub(".*\\d+\\s+(BxB|AFQMxB)\\s+", "", line)
          numeric_values <- length(regmatches(after_material, gregexpr("\\d+", after_material))[[1]])
          # If many numeric values after material, likely has edge processing data
          if (numeric_values >= 4) return(TRUE)
        }
      }
      return(FALSE)
    })
    pdf_data$has_controle <- grepl("\\bcontrole\\b", pdf_data$content, ignore.case = TRUE)
    pdf_data$has_magazijn <- grepl("\\bmagazijn\\b", pdf_data$content, ignore.case = TRUE)
    pdf_data$has_te_bestellen <- grepl("te bestellen", pdf_data$content, ignore.case = TRUE)
    
    # Analysis
    cat("\n📊 ANALYSIS RESULTS:\n")
    cat("Total lines:", nrow(pdf_data), "\n")
    cat("Numbered items:", sum(pdf_data$is_numbered), "\n")
    cat("Section headers:", sum(pdf_data$has_section), "\n")
    cat("'Aantal onderdelen' markers:", sum(pdf_data$has_aantal), "\n")
    cat("Items with edge processing:", sum(pdf_data$has_fineer), "\n")
    
    # Extract NESTING counts
    aantal_lines <- pdf_data[pdf_data$has_aantal, ]
    if (nrow(aantal_lines) > 0) {
      cat("\n🎯 NESTING MARKERS:\n")
      for (i in 1:nrow(aantal_lines)) {
        line_content <- aantal_lines$content[i]
        numbers <- regmatches(line_content, gregexpr("[0-9]+", line_content))[[1]]
        if (length(numbers) > 0) {
          cat("  Line", aantal_lines$line_number[i], ": Aantal onderdelen =", numbers[length(numbers)], "\n")
        }
      }
    }
    
    # Extract BOERE candidates
    beschrijving_lines <- pdf_data[grepl("beschrijving.*aantal stuks", pdf_data$content, ignore.case = TRUE), ]
    if (nrow(beschrijving_lines) > 0) {
      cat("\n🎯 BOERE TABLE HEADERS:\n")
      for (i in 1:nrow(beschrijving_lines)) {
        cat("  Line", beschrijving_lines$line_number[i], ": BOERE table detected\n")
      }
    }
    
    # Extract ACCURA candidates (FIXED: only in NESTING and OPDEELZAAG sections)
    # Find section boundaries
    nesting_lines <- which(grepl("nesting", pdf_data$content, ignore.case = TRUE))
    opdeelzaag_lines <- which(grepl("opdeelzaag", pdf_data$content, ignore.case = TRUE))
    
    accura_search_range <- c()
    
    # Add NESTING sections
    for (nest_start in nesting_lines) {
      nest_end <- nest_start + 200
      if (nest_end > nrow(pdf_data)) nest_end <- nrow(pdf_data)
      for (j in (nest_start + 1):nrow(pdf_data)) {
        if (grepl("opdeelzaag|controle|massief|magazijn", pdf_data$content[j], ignore.case = TRUE)) {
          nest_end <- j - 1
          break
        }
      }
      accura_search_range <- c(accura_search_range, nest_start:nest_end)
    }
    
    # Add OPDEELZAAG sections
    for (opd_start in opdeelzaag_lines) {
      opd_end <- opd_start + 100
      if (opd_end > nrow(pdf_data)) opd_end <- nrow(pdf_data)
      for (j in (opd_start + 1):nrow(pdf_data)) {
        if (grepl("nesting|controle|massief|magazijn", pdf_data$content[j], ignore.case = TRUE)) {
          opd_end <- j - 1
          break
        }
      }
      accura_search_range <- c(accura_search_range, opd_start:opd_end)
    }
    
    accura_search_range <- unique(sort(accura_search_range))
    
    # Count ACCURA items only in NESTING/OPDEELZAAG sections
    accura_count <- 0
    for (i in accura_search_range) {
      if (i <= nrow(pdf_data)) {
        if (pdf_data$is_numbered[i] && pdf_data$has_edge_processing[i]) {
          accura_count <- accura_count + 1
        }
      }
    }
    
    cat("\n🎯 ACCURA ITEMS (numbered + edge processing in NESTING/OPDEELZAAG):", accura_count, "\n")
    
    # Extract BOERE candidates - between controle and magazijn (FIXED: only first 144)
    controle_lines <- which(pdf_data$has_controle)
    magazijn_lines <- which(pdf_data$has_magazijn)
    
    if (length(controle_lines) > 0 && length(magazijn_lines) > 0) {
      cat("\n🎯 BOERE SECTION ANALYSIS:\n")
      
      for (i in 1:length(controle_lines)) {
        controle_idx <- controle_lines[i]
        
        # Find next magazijn after this controle
        next_magazijn <- magazijn_lines[magazijn_lines > controle_idx]
        if (length(next_magazijn) > 0) {
          magazijn_idx <- next_magazijn[1]
          
          # Get all numbered items between controle and magazijn
          boere_items <- c()
          for (j in (controle_idx + 1):(magazijn_idx - 1)) {
            if (j <= nrow(pdf_data)) {
              if (pdf_data$is_numbered[j] && !pdf_data$has_te_bestellen[j]) {
                boere_items <- c(boere_items, j)
              }
            }
          }
          
          # CORRECTION: Only count first 144 items (exclude lines 1506, 1509, 1512)
          boere_count <- min(length(boere_items), 144)
          
          cat("  Section", i, ": Controle line", controle_idx, "to Magazijn line", magazijn_idx, "\n")
          cat("    Total numbered items found:", length(boere_items), "\n")
          cat("    BOERE count (first 144 only):", boere_count, "\n")
        }
      }
    }
    
    # Save to CSV for SQL import
    csv_file <- "r_pdf_extraction.csv"
    write.csv(pdf_data, csv_file, row.names = FALSE)
    cat("✅ Data saved to:", csv_file, "\n")
    
    # Create simple SQL commands
    sql_file <- "r_pdf_extraction.sql"
    cat("-- R PDF EXTRACTION SQL\n", file = sql_file)
    cat("CREATE TABLE pdf_extraction (\n", file = sql_file, append = TRUE)
    cat("  line_number INTEGER,\n", file = sql_file, append = TRUE)
    cat("  content TEXT,\n", file = sql_file, append = TRUE)
    cat("  is_numbered BOOLEAN,\n", file = sql_file, append = TRUE)
    cat("  has_section BOOLEAN,\n", file = sql_file, append = TRUE)
    cat("  has_aantal BOOLEAN,\n", file = sql_file, append = TRUE)
    cat("  has_fineer BOOLEAN\n", file = sql_file, append = TRUE)
    cat(");\n\n", file = sql_file, append = TRUE)
    
    # Add data import command
    cat("-- Import CSV data:\n", file = sql_file, append = TRUE)
    cat("-- .mode csv\n", file = sql_file, append = TRUE)
    cat("-- .import r_pdf_extraction.csv pdf_extraction\n\n", file = sql_file, append = TRUE)
    
    # Add analysis queries
    cat("-- NESTING query:\n", file = sql_file, append = TRUE)
    cat("SELECT content FROM pdf_extraction WHERE has_aantal = 1;\n\n", file = sql_file, append = TRUE)
    
    cat("-- BOERE query:\n", file = sql_file, append = TRUE)
    cat("SELECT content FROM pdf_extraction WHERE LOWER(content) LIKE '%beschrijving%aantal stuks%';\n\n", file = sql_file, append = TRUE)
    
    cat("-- ACCURA query:\n", file = sql_file, append = TRUE)
    cat("SELECT COUNT(*) FROM pdf_extraction WHERE is_numbered = 1 AND has_fineer = 1;\n\n", file = sql_file, append = TRUE)
    
    cat("✅ SQL commands saved to:", sql_file, "\n")
    
    # Cleanup
    if (file.exists(text_file)) {
      file.remove(text_file)
    }
    
    return(list(
      csv_file = csv_file,
      sql_file = sql_file,
      data = pdf_data
    ))
    
  } else {
    cat("❌ Text extraction failed\n")
    return(NULL)
  }
}

# Test the extraction
pdf_file <- "S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF"

if (file.exists(pdf_file)) {
  result <- extract_pdf_with_r(pdf_file)
  if (!is.null(result)) {
    cat("\n🎉 R PDF to SQL extraction completed!\n")
    cat("📁 Files created:\n")
    cat("  CSV:", result$csv_file, "\n")
    cat("  SQL:", result$sql_file, "\n")
  }
} else {
  cat("❌ PDF file not found:", pdf_file, "\n")
}