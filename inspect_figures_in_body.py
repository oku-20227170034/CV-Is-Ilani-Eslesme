import re
from docx import Document

doc = Document("asl\u0131 s\u0131la \u00f6zate\u015f tez.docx")

print("--- ALL OCCURRENCES OF 'Şekil' WITH A NUMBER ---")
for idx, p in enumerate(doc.paragraphs):
    text = p.text.strip()
    if re.search(r"[Şş]ekil\s+\d\.\d", text):
        # Print paragraph index, text snippet, and style
        print(f"P{idx} ({p.style.name}): {text[:140]}...")
