import sys
from pathlib import Path
from io import BytesIO
import docx
import json
from dataclasses import asdict

# Add src to path
sys.path.append(str(Path.cwd()))

from src.importers.docx_importer import DocxImporter
from src.formatting import CitationFormatter
from src.models import Publication

def gen_json_results():
    importer = DocxImporter()
    filepath = "Perfect_harvard_style_references.docx"
    
    pubs = importer.parse(filepath)
    results = []
    
    for pub in pubs:
        d = asdict(pub)
        d['formatted_harvard'] = CitationFormatter.reference_entry(pub, "harvard")
        results.append(d)
        
    with open("full_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    gen_json_results()
