import sys
from pathlib import Path
from io import BytesIO
import docx
import json

# Add src to path
sys.path.append(str(Path.cwd()))

from src.importers.docx_importer import DocxImporter
from src.formatting import CitationFormatter
from src.models import Publication
from src.style.harvard_checker import HarvardStyleChecker

def test_full_document():
    importer = DocxImporter()
    checker = HarvardStyleChecker()
    
    filepath = "Perfect_harvard_style_references.docx"
    if not Path(filepath).exists():
        print(f"Error: {filepath} not found.")
        return

    pubs = importer.parse(filepath)
    
    print(f"Total references extracted: {len(pubs)}")
    print("=" * 60)
    
    for i, pub in enumerate(pubs):
        print(f"[{i+1}] Type: {pub.pub_type}")
        print(f"    Title: {pub.title}")
        if pub.editor: print(f"    Editor: {pub.editor}")
        if pub.url: print(f"    URL: {pub.url}")
        if pub.access_date: print(f"    Access Date: {pub.access_date}")
        if pub.pages: print(f"    Pages: {pub.pages}")
        
        # Check compliance
        violations = checker.check_single(pub)
        errors = [v for v in violations if v.severity == "error"]
        warnings = [v for v in violations if v.severity == "warning"]
        
        # Formatting
        formatted = CitationFormatter.reference_entry(pub, "harvard")
        print(f"    Formatted: {formatted}")
        
        if errors:
            print(f"    ERRORS: {[e.message for e in errors]}")
        if warnings:
            print(f"    WARNINGS: {[w.message for w in warnings]}")
            
        print("-" * 60)

if __name__ == "__main__":
    test_full_document()
