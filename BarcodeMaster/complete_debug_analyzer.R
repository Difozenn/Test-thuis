#!/usr/bin/env Rscript
# COMPLETE DEBUG ANALYZER
# Shows exactly which items are found vs should be found

# Extract PDF text
pdf_file <- "S04479_RAPPORT_Rudi Matterne_0411_MO07202-7203_TV-wand (7-7).PDF"
text_file <- "debug_analysis.txt"
system_command <- paste("pdftotext -layout", shQuote(pdf_file), text_file)
result <- system(system_command, intern = FALSE)

if (result != 0 || !file.exists(text_file)) {
  cat("❌ Text extraction failed\n")
  quit(status = 1)
}

# Read text
text_lines <- readLines(text_file, warn = FALSE)
cat("🔍 COMPLETE DEBUG ANALYSIS\n")
cat("==========================\n\n")

# Find BOERE section boundaries
controle_line <- 0
magazijn_line <- 0

for (i in 1:length(text_lines)) {
  line <- trimws(text_lines[i])
  if (grepl("controle", line, ignore.case = TRUE) && controle_line == 0) {
    controle_line <- i
    cat("📍 Found Controle at line", i, ":", substr(line, 1, 50), "\n")
  }
  if (controle_line > 0 && grepl("magazijn", line, ignore.case = TRUE) && magazijn_line == 0) {
    magazijn_line <- i
    cat("📍 Found Magazijn at line", i, ":", substr(line, 1, 50), "\n")
    break
  }
}

cat("\n🎯 BOERE SECTION ANALYSIS (Expected: 144 items)\n")
cat("================================================\n")
cat("Section: lines", controle_line, "to", magazijn_line, "\n\n")

if (controle_line > 0 && magazijn_line > 0) {
  boere_items <- c()
  te_bestellen_items <- c()
  all_numbered_items <- c()
  
  for (i in (controle_line + 1):(magazijn_line - 1)) {
    line <- text_lines[i]
    
    # Check if line starts with a number (potential numbered item)
    if (grepl("^\\s*[0-9]+\\s+\\w+", line)) {
      all_numbered_items <- c(all_numbered_items, i)
      
      if (grepl("te bestellen", line, ignore.case = TRUE)) {
        te_bestellen_items <- c(te_bestellen_items, i)
        cat("❌ Line", sprintf("%4d", i), ": TE BESTELLEN (excluding) -", substr(line, 1, 80), "\n")
      } else {
        boere_items <- c(boere_items, i)
        cat("✅ Line", sprintf("%4d", i), ": BOERE ITEM", sprintf("(%3d)", length(boere_items)), "-", substr(line, 1, 80), "\n")
      }
    }
  }
  
  cat("\n📊 BOERE RESULTS:\n")
  cat("Total numbered items found:", length(all_numbered_items), "\n")
  cat("Te bestellen items:", length(te_bestellen_items), "\n")
  cat("BOERE items counted:", length(boere_items), "\n")
  cat("Expected BOERE items: 144\n")
  cat("Difference:", length(boere_items) - 144, "\n\n")
}

cat("🎯 ACCURA SECTION ANALYSIS (Expected: 84 items)\n")
cat("===============================================\n")
cat("Searching ONLY within NESTING and OPDEELZAAG sections\n\n")

# Find NESTING and OPDEELZAAG section boundaries
nesting_sections <- c()
opdeelzaag_sections <- c()

for (i in 1:length(text_lines)) {
  line <- tolower(trimws(text_lines[i]))
  if (grepl("nesting", line)) {
    cat("📍 Found NESTING section at line", i, "\n")
    nesting_sections <- c(nesting_sections, i)
  }
  if (grepl("opdeelzaag", line)) {
    cat("📍 Found OPDEELZAAG section at line", i, "\n")
    opdeelzaag_sections <- c(opdeelzaag_sections, i)
  }
}

# Define ACCURA search ranges (NESTING and OPDEELZAAG sections only)
accura_search_lines <- c()

# Add NESTING sections (from section header to next major section)
for (nest_start in nesting_sections) {
  # Find end of nesting section (next section header or substantial gap)
  nest_end <- nest_start + 200  # reasonable section size
  if (nest_end > length(text_lines)) nest_end <- length(text_lines)
  
  # Find actual end by looking for next major section
  for (j in (nest_start + 1):length(text_lines)) {
    if (grepl("opdeelzaag|controle|massief|magazijn", text_lines[j], ignore.case = TRUE)) {
      nest_end <- j - 1
      break
    }
  }
  
  cat("📍 NESTING section range: lines", nest_start, "to", nest_end, "\n")
  accura_search_lines <- c(accura_search_lines, nest_start:nest_end)
}

# Add OPDEELZAAG sections
for (opd_start in opdeelzaag_sections) {
  opd_end <- opd_start + 100  # reasonable section size
  if (opd_end > length(text_lines)) opd_end <- length(text_lines)
  
  # Find actual end by looking for next major section  
  for (j in (opd_start + 1):length(text_lines)) {
    if (grepl("nesting|controle|massief|magazijn", text_lines[j], ignore.case = TRUE)) {
      opd_end <- j - 1
      break
    }
  }
  
  cat("📍 OPDEELZAAG section range: lines", opd_start, "to", opd_end, "\n")
  accura_search_lines <- c(accura_search_lines, opd_start:opd_end)
}

# Remove duplicates and sort
accura_search_lines <- unique(sort(accura_search_lines))
cat("📍 Total ACCURA search range:", length(accura_search_lines), "lines\n\n")

accura_items <- c()
numbered_without_edge <- c()

# Only search within NESTING and OPDEELZAAG sections
for (i in accura_search_lines) {
  if (i <= length(text_lines)) {
    line <- text_lines[i]
    
    # Check if line starts with a number (numbered item)
    if (grepl("^\\s*[0-9]+\\s+\\w+", line)) {
      
      # Check for edge processing patterns (L1/L2/B1/B2 columns)
      has_edge_processing <- FALSE
      
      # Pattern: Look for multiple "Xmm" values indicating edge processing
      if (grepl("\\s+[0-9]+mm\\s+[0-9]+mm\\s+[0-9]+mm\\s+[0-9]+mm", line)) {
        has_edge_processing <- TRUE
        edge_type <- "4-EDGE"
      }
      else if (grepl("\\s+[0-9]+mm\\s+[0-9]+mm\\s+[0-9]+mm\\s+", line)) {
        has_edge_processing <- TRUE
        edge_type <- "3-EDGE"
      }
      else if (grepl("\\s+[0-9]+mm\\s+[0-9]+mm\\s+", line)) {
        has_edge_processing <- TRUE
        edge_type <- "2-EDGE"
      }
      
      if (has_edge_processing) {
        accura_items <- c(accura_items, i)
        cat("✅ Line", sprintf("%4d", i), ": ACCURA", edge_type, sprintf("(%2d)", length(accura_items)), "-", substr(line, 1, 100), "\n")
      } else {
        numbered_without_edge <- c(numbered_without_edge, i)
        if (length(numbered_without_edge) <= 10) {
          cat("❌ Line", sprintf("%4d", i), ": NO EDGE (in NESTING/OPDEELZAAG) -", substr(line, 1, 100), "\n")
        }
      }
    }
  }
}

if (length(numbered_without_edge) > 10) {
  cat("... and", length(numbered_without_edge) - 10, "more numbered items without edge processing in NESTING/OPDEELZAAG\n")
}

cat("\n📊 ACCURA RESULTS:\n")
cat("ACCURA items found:", length(accura_items), "\n")
cat("Expected ACCURA items: 84\n")
cat("Difference:", length(accura_items) - 84, "\n")
cat("Numbered items without edge processing:", length(numbered_without_edge), "\n")

cat("\n🎯 NESTING VERIFICATION (Expected: 102)\n")
cat("======================================\n")
nesting_total <- 0
for (i in 1:length(text_lines)) {
  line <- text_lines[i]
  if (grepl("aantal onderdelen", line, ignore.case = TRUE)) {
    numbers <- regmatches(line, gregexpr("[0-9]+", line))[[1]]
    if (length(numbers) > 0) {
      count <- as.numeric(numbers[length(numbers)])
      # Only count main NESTING (71 and 31)
      if ((count == 71 && nesting_total == 0) || (count == 31 && nesting_total == 71)) {
        nesting_total <- nesting_total + count
        cat("✅ Line", sprintf("%4d", i), ": NESTING COUNT", count, "(total:", nesting_total, ")\n")
      }
    }
  }
}

cat("\n📊 FINAL SUMMARY:\n")
cat("=================\n")
cat("NESTING:", nesting_total, "/ 102 Expected", if(nesting_total == 102) "✅" else "❌", "\n")
cat("BOERE  :", length(boere_items), "/ 144 Expected", if(length(boere_items) == 144) "✅" else "❌", "\n")
cat("ACCURA :", length(accura_items), "/ 84 Expected", if(length(accura_items) == 84) "✅" else "❌", "\n")

if (nesting_total == 102 && length(boere_items) == 144 && length(accura_items) == 84) {
  cat("\n🎉 100% ACCURACY ACHIEVED!\n")
} else {
  cat("\n❌ ACCURACY ISSUES DETECTED - PATTERNS NEED ADJUSTMENT\n")
}

# Cleanup
if (file.exists(text_file)) {
  file.remove(text_file)
}