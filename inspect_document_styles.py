from docx import Document
from docx.shared import Pt, Cm

doc = Document("asl\u0131 s\u0131la \u00f6zate\u015f tez.docx")

print("=== DOCUMENT SECTIONS AND MARGINS ===")
for i, section in enumerate(doc.sections):
    print(f"Section {i}:")
    print(f"  Top Margin: {section.top_margin.cm if section.top_margin else None} cm (Expected: 2.5)")
    print(f"  Left Margin: {section.left_margin.cm if section.left_margin else None} cm (Expected: 4.0)")
    print(f"  Bottom Margin: {section.bottom_margin.cm if section.bottom_margin else None} cm (Expected: 3.0)")
    print(f"  Right Margin: {section.right_margin.cm if section.right_margin else None} cm (Expected: 2.5)")
    print(f"  Page Width: {section.page_width.cm if section.page_width else None} cm")
    print(f"  Page Height: {section.page_height.cm if section.page_height else None} cm")

print("\n=== PARAGRAPH PROPERTIES SAMPLE ===")
# Let's inspect a few normal paragraphs to see their font and line spacing.
normal_paras = [p for p in doc.paragraphs if p.style.name == "Normal"]
print(f"Found {len(normal_paras)} Normal paragraphs.")
for i in range(min(5, len(normal_paras))):
    p = normal_paras[i]
    if p.text.strip():
        print(f"P{i} Text: {p.text[:80]}...")
        # Inspect fonts in runs
        for run in p.runs[:2]:
            print(f"  Run Text: {run.text[:30]}")
            print(f"    Font Name: {run.font.name}")
            print(f"    Font Size: {run.font.size.pt if run.font.size else None} pt")
            print(f"    Bold: {run.font.bold}")
        # Paragraph format
        pf = p.paragraph_format
        print(f"  Line Spacing: {pf.line_spacing}")
        print(f"  Space Before: {pf.space_before.pt if pf.space_before else None}")
        print(f"  Space After: {pf.space_after.pt if pf.space_after else None}")
