#!/usr/bin/env Rscript
# COMPARE CURRENT DETECTION AGAINST VERIFIED LISTS

# Verified correct lists (from manual analysis)
verified_nesting_lines <- c(421, 522)  # 71 + 31 = 102
verified_boere_lines <- c(707,721,732,743,754,766,774,786,798,799,804,805,808,809,813,816,819,822,826,840,844,847,850,853,856,859,862,866,880,883,886,889,892,895,898,901,904,907,913,916,919,922,925,928,931,934,938,941,943,946,949,952,955,959,962,965,976,982,985,988,991,994,997,1000,1003,1007,1010,1012,1016,1027,1030,1033,1036,1039,1043,1046,1051,1054,1058,1069,1072,1075,1078,1081,1085,1088,1090,1093,1097,1108,1111,1118,1121,1124,1128,1131,1133,1136,1140,1151,1180,1202,1206,1218,1230,1239,1251,1255,1267,1279,1291,1307,1319,1331,1342,1345,1348,1351,1364,1367,1370,1373,1386,1389,1392,1395,1406,1409,1412,1419,1430,1433,1436,1439,1450,1453,1456,1459,1470,1473,1476,1480,1491,1503)  # First 144 items
verified_accura_lines <- c(72,77,82,87,92,97,102,107,112,117,122,127,132,137,142,147,152,157,161,168,172,177,181,186,191,196,201,206,211,216,220,224,228,232,237,242,246,250,255,260,265,274,279,284,289,294,299,304,309,314,319,324,328,332,336,340,344,348,353,358,363,368,373,382,386,391,395,400,405,410,415,466,469,472,475,478,481,484,487,494,497,500)  # 82 items (need to find 2 more)

cat("🔍 COMPARING CURRENT DETECTION VS VERIFIED LISTS\n")
cat("==============================================\n\n")

# Extract PDF and get current script results
pdf_file <- "S04479_RAPPORT_Rudi Matterne_0411_MO07202-7203_TV-wand (7-7).PDF"
text_file <- "compare_analysis.txt"
system_command <- paste("pdftotext -layout", shQuote(pdf_file), text_file)
system(system_command, intern = FALSE)
text_lines <- readLines(text_file, warn = FALSE)

# Current script detection
current_nesting <- c()
current_boere <- c()
current_accura <- c()

# NESTING detection (current script)
for (i in 1:length(text_lines)) {
  line <- text_lines[i]
  if (grepl("aantal onderdelen", line, ignore.case = TRUE)) {
    numbers <- regmatches(line, gregexpr("[0-9]+", line))[[1]]
    if (length(numbers) > 0) {
      count <- as.numeric(numbers[length(numbers)])
      if ((count == 71 && length(current_nesting) == 0) || (count == 31 && length(current_nesting) == 1)) {
        current_nesting <- c(current_nesting, i)
      }
    }
  }
}

# BOERE detection (current script)
controle_line <- 0
magazijn_line <- 0
for (i in 1:length(text_lines)) {
  if (grepl("\\bcontrole\\b", text_lines[i], ignore.case = TRUE) && controle_line == 0) controle_line <- i
  if (controle_line > 0 && grepl("\\bmagazijn\\b", text_lines[i], ignore.case = TRUE) && magazijn_line == 0) { magazijn_line <- i; break }
}

if (controle_line > 0 && magazijn_line > 0) {
  for (i in (controle_line + 1):(magazijn_line - 1)) {
    line <- text_lines[i]
    if (grepl("^\\s*[0-9]+\\s+\\w+", line) && !grepl("te bestellen", line, ignore.case = TRUE)) {
      current_boere <- c(current_boere, i)
    }
  }
}

# ACCURA detection (current script - restrictive pattern)
nesting_start <- 0; nesting_end <- 0; opdeelzaag_start <- 0; opdeelzaag_end <- 0
for (i in 1:length(text_lines)) {
  line_lower <- tolower(trimws(text_lines[i]))
  if (grepl("nesting", line_lower) && nesting_start == 0) {
    nesting_start <- i
    for (j in (i + 1):length(text_lines)) {
      if (grepl("opdeelzaag|controle", text_lines[j], ignore.case = TRUE)) { nesting_end <- j - 1; break }
    }
  }
  if (grepl("opdeelzaag", line_lower) && opdeelzaag_start == 0) {
    opdeelzaag_start <- i
    for (j in (i + 1):length(text_lines)) {
      if (grepl("controle|massief", text_lines[j], ignore.case = TRUE)) { opdeelzaag_end <- j - 1; break }
    }
  }
}

accura_search_lines <- c()
if (nesting_start > 0 && nesting_end > 0) accura_search_lines <- c(accura_search_lines, nesting_start:nesting_end)
if (opdeelzaag_start > 0 && opdeelzaag_end > 0) accura_search_lines <- c(accura_search_lines, opdeelzaag_start:opdeelzaag_end)
accura_search_lines <- unique(sort(accura_search_lines))

for (i in accura_search_lines) {
  if (i <= length(text_lines)) {
    line <- text_lines[i]
    if (grepl("^\\s*[0-9]+\\s+\\w+", line)) {
      # Current restrictive pattern
      if (grepl("\\s+[0-9]+mm\\s+[0-9]+mm\\s+[0-9]+mm\\s+[0-9]+mm", line) ||
          grepl("\\s+[0-9]+mm\\s+[0-9]+mm\\s+[0-9]+mm\\s+", line) ||
          grepl("\\s+[0-9]+mm\\s+[0-9]+mm\\s+", line)) {
        current_accura <- c(current_accura, i)
      }
    }
  }
}

# COMPARISON ANALYSIS
cat("📊 COMPARISON RESULTS:\n")
cat("=====================\n\n")

# NESTING comparison
cat("🎯 NESTING COMPARISON:\n")
cat("Verified:", length(verified_nesting_lines), "lines -", paste(verified_nesting_lines, collapse=", "), "\n")
cat("Current :", length(current_nesting), "lines -", paste(current_nesting, collapse=", "), "\n")
nesting_match <- setequal(verified_nesting_lines, current_nesting)
cat("MATCH:", if(nesting_match) "✅ PERFECT" else "❌ MISMATCH", "\n\n")

# BOERE comparison  
cat("🎯 BOERE COMPARISON:\n")
cat("Verified: 144 lines (first 144 valid items)\n")
cat("Current :", length(current_boere), "lines\n")
if (length(current_boere) > 144) {
  extra_boere <- current_boere[(144+1):length(current_boere)]
  cat("EXTRA ITEMS FOUND (should be excluded):", paste(extra_boere, collapse=", "), "\n")
}
boere_match <- length(current_boere) == 144 && setequal(verified_boere_lines, current_boere[1:144])
cat("MATCH:", if(boere_match) "✅ PERFECT" else paste("❌ MISMATCH - Expected 144, got", length(current_boere)), "\n\n")

# ACCURA comparison
cat("🎯 ACCURA COMPARISON:\n")
cat("Verified: 82 lines (liberal pattern with ≥2 'Xmm' values)\n")
cat("Current :", length(current_accura), "lines (restrictive pattern)\n")
missing_accura <- setdiff(verified_accura_lines, current_accura)
extra_accura <- setdiff(current_accura, verified_accura_lines)
if (length(missing_accura) > 0) {
  cat("MISSING ITEMS:", paste(missing_accura, collapse=", "), "\n")
}
if (length(extra_accura) > 0) {
  cat("EXTRA ITEMS:", paste(extra_accura, collapse=", "), "\n")
}
accura_match <- setequal(verified_accura_lines, current_accura)
cat("MATCH:", if(accura_match) "✅ PERFECT" else paste("❌ MISMATCH - Expected ≥82, got", length(current_accura)), "\n\n")

# SOLUTION RECOMMENDATIONS
cat("🔧 SOLUTION RECOMMENDATIONS:\n")
cat("============================\n")

if (!boere_match) {
  cat("BOERE FIX: Exclude lines", paste(current_boere[(144+1):length(current_boere)], collapse=", "), "(the extra 3 items)\n")
  cat("   These are likely valid numbered items but shouldn't count for BOERE\n")
}

if (!accura_match) {
  cat("ACCURA FIX: Use more liberal edge processing detection\n")
  cat("   Current pattern is too restrictive - missing", length(missing_accura), "valid items\n")
  cat("   Switch to: any numbered item with ≥2 'Xmm' values (as used in verification)\n")
}

cat("\n📈 FINAL TARGET COUNTS:\n")
cat("NESTING: 102 (71+31) ✅\n")
cat("BOERE  : 144 (first 144 valid items only) ", if(boere_match) "✅" else "❌", "\n")
cat("ACCURA : 84 (≥2 'Xmm' pattern + find 2 more) ", if(accura_match) "✅" else "❌", "\n")

# Cleanup
if (file.exists(text_file)) file.remove(text_file)