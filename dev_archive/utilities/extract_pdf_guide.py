import sys
from pathlib import Path
try:
    from PyPDF2 import PdfReader
except ImportError:
    print("PyPDF2 not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pypdf2"])
    from PyPDF2 import PdfReader

import json

def extract_pdf_content():
    """Extract text from Harvard referencing guide PDF."""
    pdf_path = "Harvard referencing guide.pdf"
    
    if not Path(pdf_path).exists():
        print(f"Error: {pdf_path} not found")
        return
    
    reader = PdfReader(pdf_path)
    
    all_text = []
    for page_num, page in enumerate(reader.pages, 1):
        text = page.extract_text()
        if text:
            all_text.append(f"=== PAGE {page_num} ===\n{text}")
    
    # Save full content
    with open("harvard_guide_full.txt", "w", encoding="utf-8") as f:
        f.write("\n\n".join(all_text))
    
    print(f"Extracted {len(reader.pages)} pages")
    print(f"Saved to harvard_guide_full.txt")
    
    # Print first 2 pages for preview
    print("\n=== PREVIEW (First 2 Pages) ===\n")
    for text in all_text[:2]:
        print(text)
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    extract_pdf_content()
