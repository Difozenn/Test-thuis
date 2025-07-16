# R PDF EXTRACTOR
# R language has superior PDF extraction capabilities

# Install required packages
if (!require("pdftools")) install.packages("pdftools")
if (!require("tabulizer")) install.packages("tabulizer")
if (!require("tidyverse")) install.packages("tidyverse")
if (!require("DBI")) install.packages("DBI")
if (!require("RSQLite")) install.packages("RSQLite")

library(pdftools)
library(tabulizer)
library(tidyverse)
library(DBI)
library(RSQLite)

# Function to extract PDF data to SQL
extract_pdf_to_sql <- function(pdf_path) {
  
  cat("🔍 R PDF EXTRACTION TO SQL\n")
  cat("========================\n")
  
  # Method 1: Extract text with pdftools
  cat("📄 Extracting text...\n")
  text_content <- pdf_text(pdf_path)
  
  # Method 2: Extract tables with tabulizer
  cat("📊 Extracting tables...\n")
  tables <- extract_tables(pdf_path, pages = 1:10, method = "lattice")
  
  # Create SQLite database
  db_file <- "pdf_extraction.db"
  con <- dbConnect(RSQLite::SQLite(), db_file)
  
  # Process text content
  text_lines <- unlist(strsplit(paste(text_content, collapse = "\n"), "\n"))
  text_df <- data.frame(
    page = rep(1:length(text_content), sapply(strsplit(text_content, "\n"), length)),
    line_number = sequence(sapply(strsplit(text_content, "\n"), length)),
    content = text_lines,
    stringsAsFactors = FALSE
  )
  
  # Store text in SQL
  dbWriteTable(con, "pdf_text", text_df, overwrite = TRUE)
  
  # Process tables
  if (length(tables) > 0) {
    for (i in seq_along(tables)) {
      table_data <- as.data.frame(tables[[i]])
      table_name <- paste0("pdf_table_", i)
      dbWriteTable(con, table_name, table_data, overwrite = TRUE)
    }
  }
  
  # Extract NESTING counts
  nesting_query <- "
    SELECT content, page, line_number 
    FROM pdf_text 
    WHERE LOWER(content) LIKE '%aantal onderdelen%'
  "
  nesting_results <- dbGetQuery(con, nesting_query)
  cat("✅ Found", nrow(nesting_results), "NESTING markers\n")
  
  # Extract numbered items
  numbered_query <- "
    SELECT content, page, line_number 
    FROM pdf_text 
    WHERE content REGEXP '^[0-9]+[[:space:]]'
  "
  numbered_results <- dbGetQuery(con, numbered_query)
  cat("✅ Found", nrow(numbered_results), "numbered items\n")
  
  # Close database
  dbDisconnect(con)
  
  cat("✅ SQL database created:", db_file, "\n")
  return(db_file)
}

# Test the extraction
pdf_file <- "S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF"

if (file.exists(pdf_file)) {
  result_db <- extract_pdf_to_sql(pdf_file)
  cat("🎯 SQL extraction completed!\n")
} else {
  cat("❌ PDF file not found:", pdf_file, "\n")
}