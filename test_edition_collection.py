import sys
from pathlib import Path
from io import BytesIO
import docx

# Add src to path
sys.path.append(str(Path.cwd()))

from src.importers.docx_importer import DocxImporter
from src.formatting import CitationFormatter

def test_edition_collection():
    """Test edition and collection extraction."""
    importer = DocxImporter()
    doc = docx.Document()
    
    # Test cases from Harvard guide
    examples = [
        # Book with edition
        "Pfleeger, C. P. and Pfleeger, S. L.(2006) Security in computing. 4th edn. Upper Saddle River,NJ: Prentice Hall.",
        # E-book with collection
        "Peikari,C. and Chuvakin, A. (2004) Security warrior. Safari Books Online [Online]. Available at: http://www.safaribooksonline.com (Accessed: 7 September 2009).",
        # E-journal with collection
        "Duta, N. (2009) 'A Survey of biometric technology based on hand shape', Pattern Recognition, 42(11), pp.2797-2806. ACM Digital Library [Online]. Available at: http://portal.acm.org.ezproxy.kingston.ac.uk/ (Accessed: 7 September 2009).",
        # Book without edition (should suggest)
        "Stajano,F. (2002) Security for ubiquitous computing. Chichester: John Wiley & Sons."
    ]
    
    for ex in examples:
        doc.add_paragraph(ex)
    
    stream = BytesIO()
    doc.save(stream)
    stream.seek(0)
    
    pubs = importer.parse(stream)
    
    print(f"Total parsed: {len(pubs)}")
    print("=" * 80)
    
    for i, pub in enumerate(pubs, 1):
        print(f"\n[{i}] {pub.title}")
        print(f"    Type: {pub.pub_type}")
        print(f"    Edition: '{pub.edition}' {'[YES]' if pub.edition else '[NO]'}")
        print(f"    Collection: '{pub.collection}' {'[YES]' if pub.collection else '[NO]'}")
        if pub.url:
            print(f"    URL: {pub.url[:50]}...")
        print("-" * 80)

if __name__ == "__main__":
    test_edition_collection()
