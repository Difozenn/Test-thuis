import re

text = r"000000277360;Y:\OPUS\KORPUS\1013_MO6798_Vestiaire_(16-16)\MW_01Spiegeldeur_L_01_L.HOP"
print(f"Input text: {text}")

match = re.search(r'(MO\d{4,5})', text, re.IGNORECASE)
if match:
    print(f"Match found: {match.group(1)}")
else:
    print("No match found")
    
# Try to find MO in the text
if 'MO' in text.upper():
    print(f"MO found in text at position: {text.upper().index('MO')}")
    # Show surrounding characters
    pos = text.upper().index('MO')
    print(f"Context: ...{text[max(0,pos-5):min(len(text),pos+10)]}...")
