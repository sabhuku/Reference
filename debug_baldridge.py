import sys
from pathlib import Path
from io import BytesIO
import docx

# Add src to path
sys.path.append(str(Path.cwd()))

from src.importers.docx_importer import DocxImporter
from src.formatting import CitationFormatter

def debug_baldridge():
    importer = DocxImporter()
    doc = docx.Document()
    ex = "Baldridge, J.V., Curtis, D.V. Euchre, G and Riley, G.L. (2005) Effective Communication Dublin: Gill and Macmillan"
    doc.add_paragraph(ex)
    
    stream = BytesIO()
    doc.save(stream)
    stream.seek(0)
    
    pubs = importer.parse(stream)
    if not pubs:
        print("Failed to parse")
        return
        
    pub = pubs[0]
    print(f"Type: {pub.pub_type}")
    print(f"Title: '{pub.title}'")
    print(f"Location: '{pub.location}'")
    print(f"Publisher: '{pub.publisher}'")
    
    formatted = CitationFormatter.reference_entry(pub, "harvard")
    print(f"Formatted: {formatted}")

if __name__ == "__main__":
    debug_baldridge()
