-- R PDF EXTRACTION SQL
CREATE TABLE pdf_extraction (
  line_number INTEGER,
  content TEXT,
  is_numbered BOOLEAN,
  has_section BOOLEAN,
  has_aantal BOOLEAN,
  has_fineer BOOLEAN
);

-- Import CSV data:
-- .mode csv
-- .import r_pdf_extraction.csv pdf_extraction

-- NESTING query:
SELECT content FROM pdf_extraction WHERE has_aantal = 1;

-- BOERE query:
SELECT content FROM pdf_extraction WHERE LOWER(content) LIKE '%beschrijving%aantal stuks%';

-- ACCURA query:
SELECT COUNT(*) FROM pdf_extraction WHERE is_numbered = 1 AND has_fineer = 1;

