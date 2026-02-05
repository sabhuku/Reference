"""Pure logic for generating Harvard compliance reports."""
from typing import List, Dict
from collections import Counter

from .models import Violation, ReferenceCompliance, ComplianceReport, ComplianceStats, ReferenceMetadata

class HarvardComplianceReportGenerator:
    """
    Generates compliance reports from pre-computed data.
    Deterministic and side-effect free.
    """

    def generate(self, 
                 references: List[ReferenceMetadata], 
                 violations: List[Violation]) -> ComplianceReport:
        """
        Generate a report from metadata and flat list of violations.
        Violations must have reference_id set to match references.id.
        """
        
        # Index violations by reference_id
        violation_map: Dict[str, List[Violation]] = {ref.id: [] for ref in references}
        stats = ComplianceStats()
        
        flat_violations = [] # For summary stats logic (excluding info)
        
        for v in violations:
            if v.reference_id in violation_map:
                violation_map[v.reference_id].append(v)
                
                # Update counters (info is suggestion/counting but not scoring penalty)
                if v.severity == 'error':
                    stats.errors += 1
                    flat_violations.append(v)
                elif v.severity == 'warning':
                    stats.warnings += 1
                    flat_violations.append(v)
                elif v.severity == 'info':
                    stats.suggestions += 1
        
        # Build ReferenceCompliance objects
        details = []
        for ref in references:
            ref_violations = violation_map.get(ref.id, [])
            # Calculate per-reference score
            # Stricter penalties: Error=40 (Major defect), Warning=10 (Minor defect)
            ref_deduction = sum(40.0 for v in ref_violations if v.severity == 'error') + \
                            sum(10.0 for v in ref_violations if v.severity == 'warning')
            ref_score = max(0.0, 100.0 - ref_deduction)
            
            details.append(ReferenceCompliance(
                reference_key=ref.id,
                display_title=ref.display_title,
                normalised_reference=getattr(ref, 'formatted_ref', ref.display_title),
                compliance_score=ref_score,
                violations=ref_violations,
                provenance=ref.provenance
            ))
            
        # Calculate overall score (Advisory)
        if len(references) > 0:
            avg_score = sum(d.compliance_score for d in details) / len(references)
            score = avg_score
        else:
            score = 100.0
        
        # Generate summary
        summary = self._generate_marker_summary(score, flat_violations)
        
        return ComplianceReport(
            style="Harvard",
            style_version="v1.0 (Advisory)",
            overall_compliance_score=score,
            summary=summary,
            counts=stats,
            references=details
        )
    
    def _calculate_score(self, stats: ComplianceStats, total_refs: int) -> float:
        """Deprecated internal calculator, logic moved to generate."""
        return 0.0

    def _generate_marker_summary(self, score: float, violations: List[Violation]) -> str:
        """Generate neutral, marker-facing summary text."""
        has_errors = any(v.severity == 'error' for v in violations)
        
        if not violations and score == 100:
            return "Referencing appears compliant with Harvard standards."
            
        if has_errors:
            # Neutral phrasing for errors
            rule_counts = Counter(v.rule_id for v in violations if v.severity == 'error')
            if rule_counts:
                most_common_rule, _ = rule_counts.most_common(1)[0]
                suggestion = self._get_feedback_category(most_common_rule)
                return f"Referencing is functional but contains errors. Please review requirements for {suggestion}."
            return "Referencing contains errors that require attention."

        # No errors, but maybe warnings or just lower score (unlikely if no violations)
        if score >= 90:
            return "Referencing is largely compliant."
        
        # Warnings present
        rule_counts = Counter(v.rule_id for v in violations)
        most_common_rule, _ = rule_counts.most_common(1)[0]
        suggestion = self._get_feedback_category(most_common_rule)
        
        return f"Referencing is largely compliant, but attention is needed for {suggestion}."

    def _get_feedback_category(self, rule_id: str) -> str:
        """Map rule ID to friendly feedback category."""
        mapping = {
            "HARVARD.AUTHOR.MISSING": "author attribution",
            "HARVARD.AUTHOR.FORMAT": "author name formatting",
            "HARVARD.YEAR.MISSING": "publication dates",
            "HARVARD.TITLE.MISSING": "titles",
            "HARVARD.TITLE.CAPITALIZATION": "title capitalization",
            "HARVARD.JOURNAL.MISSING": "journal names",
            "HARVARD.BOOK.PUBLISHER_MISSING": "publisher details",
            "HARVARD.BOOK.LOCATION_MISSING": "publication location",
            "HARVARD.JOURNAL.DETAILS_MISSING": "journal volume/issue details",
            "HARVARD.DOI_OR_URL.MISSING": "digital object identifiers (DOIs)"
        }
        return mapping.get(rule_id, "referencing rules")
