"""Reporting logic for Harvard compliance."""
from typing import List

from ..models import Publication
from .models import Violation, ComplianceReport, ReferenceMetadata
from .harvard_checker import HarvardStyleChecker
from .report_generator import HarvardComplianceReportGenerator

class HarvardComplianceReporter:
    """
    Orchestrator for compliance reporting.
    Connects Checker (logic) with Generator (reporting).
    """
    
    def __init__(self):
        self.checker = HarvardStyleChecker()
        self.generator = HarvardComplianceReportGenerator()
        
    def generate_report(self, publications: List[Publication]) -> ComplianceReport:
        """Generate a full compliance report from raw publications."""
        from ..normalizer import ReferenceNormalizer
        from ..formatting import CitationFormatter
        
        # 1. Normalize Publications
        # This modifies publications in-place with normalized fields and logs
        for pub in publications:
            ReferenceNormalizer.normalize(pub)
            
        # 2. Check all publications
        # Returns List[List[Violation]] aligned with publications
        violations_per_pub = self.checker.check_publications(publications)
        
        # 3. Prepare metadata and flatten violations with IDs
        metadata_list = []
        flat_violations = []
        
        for i, (pub, pub_violations) in enumerate(zip(publications, violations_per_pub)):
            # Generate ID
            ref_id = self._generate_key(pub, i)
            
            # Generate Display Title (Simplified)
            title = pub.title if pub.title else "Untitled"
            auth_summary = "Unknown Author"
            if pub.normalized_authors:
                auth_summary = pub.normalized_authors[0]
                if len(pub.normalized_authors) > 1:
                    auth_summary += " et al."
            elif pub.authors:
                auth_summary = pub.authors[0]
                if len(pub.authors) > 1:
                    auth_summary += " et al."
                    
            year_val = pub.year if pub.year else "n.d."
            display_title = f"{title} ({auth_summary}, {year_val})"
            
            # Generate Full Formatted Reference
            formatted_ref = CitationFormatter.reference_entry(pub, "harvard")
            
            # Extract Provenance
            provenance = {
                'authors_inferred': getattr(pub, 'authors_inferred', False),
                'year_status': getattr(pub, 'year_status', 'present'),
                'source_type_inferred': getattr(pub, 'source_type_inferred', False),
                'normalization_log': getattr(pub, 'normalization_log', [])
            }
            
            metadata_list.append(ReferenceMetadata(
                id=ref_id,
                display_title=display_title,
                formatted_ref=formatted_ref,
                provenance=provenance
            ))
            
            # Enrich violations with ref_id
            for v in pub_violations:
                v.reference_id = ref_id
                flat_violations.append(v)
        
        # 4. Generate Report
        return self.generator.generate(metadata_list, flat_violations)
        
    def _generate_key(self, pub: Publication, index: int) -> str:
        """Generate a stable, unique citation key."""
        base_key = f"Ref{index+1}"
        
        if pub.authors and pub.year:
            try:
                # Attempt AuthorYear format
                first_auth = pub.authors[0].split(',')[0].strip().split()[-1].lower()
                y = ''.join(filter(str.isdigit, str(pub.year)))
                if not y: y = "nd"
                base_key = f"{first_auth}{y}"
            except:
                pass
        
        # Ensure Uniqueness by appending index
        # This prevents violation merging if multiple papers map to same AuthorYear
        return f"{base_key}_{index}"


