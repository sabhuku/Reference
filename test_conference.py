import sys
from pathlib import Path
from io import BytesIO
import docx

# Add src to path
sys.path.append(str(Path.cwd()))

from src.importers.docx_importer import DocxImporter
from src.formatting import CitationFormatter
from src.style.harvard_checker import HarvardStyleChecker

def test_conference_support():
    """Test conference paper detection, extraction, and formatting."""
    importer = DocxImporter()
    formatter = CitationFormatter()
    checker = HarvardStyleChecker()
    
    doc = docx.Document()
    
    # Test cases for conference papers
    examples = [
        "Smith, J. (2020) 'Machine learning in healthcare', International Conference on AI, London, UK, 15-17 June, pp. 45-52.",
        "Brown, A. and Green, B. (2019) 'Data privacy concerns', IEEE Symposium on Security, San Francisco, USA, pp. 123-130.",
        "Taylor, C. (2021) 'Climate modeling', World Climate Congress, Paris, France, 1-5 December, pp. 78-85.",
        # Compare with journal article
        "Sridhar, S. (2025) 'Constructive peer review made practical: a guide to the EMPATHY framework', Journal of Marketing, 89(3), pp. 1-12."
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
        print(f"    Authors: {', '.join(pub.authors[:2])}")
        
        if pub.pub_type == "conference":
            print(f"    Conference: {pub.conference_name}")
            print(f"    Location: {pub.conference_location}")
            print(f"    Date: {pub.conference_date}")
            print(f"    Pages: {pub.pages}")
        elif pub.pub_type == "article":
            print(f"    Journal: {pub.journal}")
        
        # Format and validate
        formatted = formatter.reference_entry(pub, style="harvard")
        print(f"\n    Formatted:\n    {formatted}")
        
        violations = checker.check_single(pub)
        if violations:
            print(f"\n    Violations ({len(violations)}):")
            for v in violations:
                print(f"      - [{v.severity.upper()}] {v.message}")
        else:
            print(f"\n    [PASS] No violations")
        
        print("-" * 80)

if __name__ == "__main__":
    test_conference_support()
