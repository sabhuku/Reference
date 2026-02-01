import sys
from pathlib import Path
from io import BytesIO
import docx

# Add src to path
sys.path.append(str(Path.cwd()))

from src.importers.docx_importer import DocxImporter
from src.formatting import CitationFormatter
from src.models import Publication

def test_specialized_coverage():
    importer = DocxImporter()
    
    # Simulate the user's document using the clean_references.txt we extracted earlier
    # or just create a small docx for testing the key types
    doc = docx.Document()
    examples = [
        "Bell, J. (2014) Doing your research project. Open University Press.", # Book
        "Adams, D. (1979) The Hitchhiker's Guide to the galaxy. Pan. Available at: http://www.amazon.co.uk/kindle-ebooks (Accessed: 23 June 2021).", # Web Book/Ebook
        "Franklin, A.W. (2012) 'Management of the problem', in S.M. Smith (ed.) The maltreatment of children. MTP, pp. 83–95.", # Chapter
        "Sridhar, S. (2025) 'Constructive peer review made practical: a guide to the EMPATHY framework', Journal of Marketing, 89(3), pp. 1-12.", # Article
        "Frazier, D.R. (2016) The Colosseum in Rome, Italy [Photograph]. Available at: https://quest.eb.com/images (Accessed: 1 September 2025).", # Image
        "O'Mahony, N. (2024) ‘How the course works’, Welcome forum, in A215: Creative writing. Available at: https://learn2.open.ac.uk (Accessed: 24 January 2025).", # Forum
        "Rietdorf, K. and Bootman, M. (2024) 'Topic 3: rare diseases'. S290: Investigating human health and disease. Available at: https://learn2.open.ac.uk (Accessed: 24 January 2025).", # Module
        "Baldridge, J.V., Curtis, D.V. Euchre, G and Riley, G.L. (2005) Effective Communication Dublin: Gill and Macmillan" # Missing period book case
    ]
    
    for ex in examples:
        doc.add_paragraph(ex)
    
    stream = BytesIO()
    doc.save(stream)
    stream.seek(0)
    
    pubs = importer.parse(stream)
    
    print(f"Total parsed: {len(pubs)}")
    print("-" * 20)
    
    for i, pub in enumerate(pubs):
        print(f"[{i+1}] Type: {pub.pub_type}")
        print(f"    Title: {pub.title}")
        if pub.url: print(f"    URL: {pub.url}")
        if pub.access_date: print(f"    Access: {pub.access_date}")
        if pub.editor: print(f"    Editor: {pub.editor}")
        
        formatted = CitationFormatter.reference_entry(pub, "harvard")
        print(f"    Formatted: {formatted}")
        print("-" * 40)

if __name__ == "__main__":
    test_specialized_coverage()
