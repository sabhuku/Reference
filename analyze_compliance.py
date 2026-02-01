import sys
from pathlib import Path
from io import BytesIO
import docx
from collections import Counter
import uuid

# Add src to path
sys.path.append(str(Path.cwd()))

from src.importers.docx_importer import DocxImporter
from src.style.harvard_checker import HarvardStyleChecker
from src.style.report_generator import HarvardComplianceReportGenerator
from src.style.models import ReferenceMetadata, Violation
from src.formatting import CitationFormatter

def analyze_compliance():
    importer = DocxImporter()
    checker = HarvardStyleChecker()
    
    filepath = "Perfect_harvard_style_references.docx"
    pubs = importer.parse(filepath)
    
    references_meta = []
    all_violations = []
    
    for pub in pubs:
        ref_id = str(uuid.uuid4())
        formatted = CitationFormatter.reference_entry(pub, "harvard")
        meta = ReferenceMetadata(id=ref_id, display_title=pub.title, formatted_ref=formatted)
        references_meta.append(meta)
        violations = checker.check_single(pub)
        for v in violations:
            v.reference_id = ref_id
            all_violations.append(v)
            
    generator = HarvardComplianceReportGenerator()
    report = generator.generate(references_meta, all_violations)
    
    print(f"Overall Score: {report.overall_score:.2f}%")
    print("\n--- BALDRIDGE CHECK ---")
    for res in report.details:
        if "Baldridge" in res.normalised_reference:
            print(f"Baldridge Score: {res.compliance_score}%")
            for v in res.violations:
                 print(f"  - {v.severity.upper()}: {v.message}")

    print("\n--- TOP VIOLATIONS ---")
    tally = Counter(v.rule_id for v in all_violations if v.severity in ['error', 'warning'])
    for rule, count in tally.most_common(5):
        print(f"{rule}: {count}")

    print("\n--- SAMPLE DEDUCTION ---")
    # Show references with exactly 85% (one warning)
    shown = 0
    for res in report.details:
        if res.compliance_score == 85.0 and shown < 5:
            print(f"[{res.display_title}] -> {res.normalised_reference}")
            for v in res.violations:
                print(f"   - {v.message}")
            shown += 1

if __name__ == "__main__":
    analyze_compliance()
