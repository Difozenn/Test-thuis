
import pdfplumber
import re
import pandas as pd

pdf_path = "S04479_RAPPORT_Rudi Matterne_0411_MO07202-7203_TV-wand (7-7).PDF"  # TV-wand PDF

# Initialize counters
count1_nesting = 0
count1_opdeelzaag = 0
count2_nesting = 0
count2_opdeelzaag = 0
count3 = 0
count3_lines = []

# === Count 1 & Count 2: Extract Nesting and Opdeelzaag sections ===
with pdfplumber.open(pdf_path) as pdf:
    for i, page in enumerate(pdf.pages):
        text = page.extract_text()
        if not text:
            continue
        lines = text.splitlines()

        section = None
        if any("Nesting" in line for line in lines):
            section = "nesting"
        elif any("Opdeelzaag" in line for line in lines):
            section = "opdeelzaag"
        else:
            continue

        current_block = []
        for line in lines:
            if re.match(r'^\d+\s+\S+', line):
                if current_block:
                    block_text = " ".join(current_block)
                    if section == "nesting":
                        count1_nesting += 1
                    elif section == "opdeelzaag":
                        count1_opdeelzaag += 1

                    if any(x in block_text for x in ["L1", "L2", "B1", "B2"]):
                        if section == "nesting":
                            count2_nesting += 1
                        elif section == "opdeelzaag":
                            count2_opdeelzaag += 1

                current_block = [line]
            else:
                current_block.append(line)

        # handle last block on page
        if current_block:
            block_text = " ".join(current_block)
            if section == "nesting":
                count1_nesting += 1
            elif section == "opdeelzaag":
                count1_opdeelzaag += 1

            if any(x in block_text for x in ["L1", "L2", "B1", "B2"]):
                if section == "nesting":
                    count2_nesting += 1
                elif section == "opdeelzaag":
                    count2_opdeelzaag += 1

# === Count 3: Dynamic block detection between Controle MO and Magazijn MO ===
inside_block = False
start_pattern = re.compile(r"Controle\s+MO")
end_pattern = re.compile(r"Magazijn\s+MO")

with pdfplumber.open(pdf_path) as pdf:
    for i, page in enumerate(pdf.pages):
        lines = page.extract_text().splitlines() if page.extract_text() else []

        for j in range(len(lines)):
            line = lines[j]
            joined_line = line + (" " + lines[j + 1] if j + 1 < len(lines) else "")

            if not inside_block and re.search(start_pattern, joined_line):
                inside_block = True
                continue

            if inside_block and re.search(end_pattern, joined_line):
                inside_block = False
                break

            if inside_block and re.match(r'^\d+\s+\S+', line) and "te bestellen" not in line.lower():
                count3 += 1
                count3_lines.append((i + 1, line))

# === Save results ===
summary_data = {
    "Metric": [
        "Count1 - Nesting Items",
        "Count1 - Opdeelzaag Items",
        "Count1 - Total",
        "Count2 - Nesting with L/B Sides",
        "Count2 - Opdeelzaag with L/B Sides",
        "Count2 - Total with L/B Sides",
        "Count3 - Valid Items from Controle MO to Magazijn MO"
    ],
    "Value": [
        count1_nesting,
        count1_opdeelzaag,
        count1_nesting + count1_opdeelzaag,
        count2_nesting,
        count2_opdeelzaag,
        count2_nesting + count2_opdeelzaag,
        count3
    ]
}

df_summary = pd.DataFrame(summary_data)
df_summary.to_excel("pdf_counts_summary.xlsx", index=False)

df_count3 = pd.DataFrame(count3_lines, columns=["Page", "Line"])
df_count3.to_excel("count3_rows.xlsx", index=False)

print("Dynamic counts exported successfully.")
