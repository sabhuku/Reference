import sys
from pathlib import Path
from docx import Document
import json

def extract_guide_content():
    """Extract structured content from Harvard referencing guide."""
    doc_path = "Harvard referencing guide.doc"
    
    if not Path(doc_path).exists():
        print(f"Error: {doc_path} not found")
        return
    
    doc = Document(doc_path)
    
    # Extract all text
    all_text = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            all_text.append(text)
    
    # Save to JSON for analysis
    output = {
        "total_paragraphs": len(all_text),
        "content": all_text[:200]  # First 200 paragraphs
    }
    
    with open("harvard_guide_extract.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"Extracted {len(all_text)} paragraphs")
    print("\n=== FIRST 50 PARAGRAPHS ===\n")
    for i, text in enumerate(all_text[:50], 1):
        print(f"{i}. {text}")

if __name__ == "__main__":
    extract_guide_content()
