"""Student-facing remediation generator."""
from dataclasses import dataclass, field
from typing import List, Dict, Literal

from .models import ComplianceReport, Violation

@dataclass
class RemediationAction:
    """A single piece of constructive feedback."""
    priority: Literal['High', 'Medium', 'Low']
    action: str
    explanation: str

@dataclass
class ReferenceRemediation:
    """Remediation set for a specific reference."""
    reference_key: str
    display_title: str
    actions: List[RemediationAction] = field(default_factory=list)

@dataclass
class StudentFeedbackReport:
    """Full student-facing feedback report."""
    references: List[ReferenceRemediation]

class RemediationGenerator:
    """
    Transforms compliance reports into student guidance.
    Pure, side-effect free, non-judgemental.
    """
    
    # Mapping Rule ID -> (Action, Explanation)
    _GUIDANCE_MAP = {
        "HARVARD.AUTHOR.MISSING": (
            "Please check if an author or organisation is available.",
            "Attributing work to its creator is central to academic integrity. If no specific author exists, consider if a corporate author (e.g., 'World Health Organization') is appropriate."
        ),
        "HARVARD.AUTHOR.FORMAT": (
            "Review the formatting of the author's name.",
            "Standard naming conventions (typically 'Surname, Initial') ensure consistency and help readers locate the correct author in alphabetical lists."
        ),
        "HARVARD.YEAR.MISSING": (
            "Check for a publication year.",
            "Providing a date helps the reader understand the currency and context of the source. If truly undated, 'n.d.' is the standard convention."
        ),
        "HARVARD.TITLE.MISSING": (
            "Ensure the work has a title.",
            "The title is the primary way readers identify the specific source you are citing."
        ),
        "HARVARD.TITLE.CAPITALIZATION": (
            "Adjust the capitalization of the title.",
            "Consistent capitalization (typically sentence case or title case) improves readability and professional presentation."
        ),
        "HARVARD.JOURNAL.MISSING": (
            "Include the name of the journal.",
            "For articles, the journal name is essential to identify where the work was published and verify its source."
        ),
        "HARVARD.BOOK.PUBLISHER_MISSING": (
            "Add the name of the publisher.",
            "Publisher details indicate the authority behind the book and assist in locating the specific edition."
        ),
        "HARVARD.BOOK.LOCATION_MISSING": (
            "Check if a place of publication is available.",
            "Including the city of publication distinguishes between different international offices of a publisher."
        ),
        "HARVARD.JOURNAL.DETAILS_MISSING": (
            "Verify if volume, issue, or page numbers are available.",
            "Specific details like volume and page numbers allow the reader to find the exact article within a journal archive."
        ),
        "HARVARD.DOI_OR_URL.MISSING": (
            "Consider adding a DOI or stable URL.",
            "Digital Object Identifiers (DOIs) provide a permanent link to the source, which is helpful for online articles."
        ),
        "NORMALIZATION.INFO": (
            "Note: Automatic formatting applied.",
            "The system adjusted this field to match standard conventions. Please verify the change is correct."
        )
    }

    def generate(self, compliance_report: ComplianceReport) -> StudentFeedbackReport:
        """Generate student feedback from a compliance report."""
        
        remediated_refs = []
        
        for ref_compliance in compliance_report.details:
            actions = []
            
            # Map violations to actions
            for v in ref_compliance.violations:
                guide = self._GUIDANCE_MAP.get(v.rule_id)
                if guide:
                    action_text, explanation = guide
                    priority = self._map_severity(v.severity)
                    
                    actions.append(RemediationAction(
                        priority=priority,
                        action=action_text,
                        explanation=explanation
                    ))
                else:
                    # Fallback for unknown rules
                    actions.append(RemediationAction(
                        priority="Low",
                        action="Review this element for consistency.",
                        explanation="Ensuring all parts of the citation are complete helps clarity."
                    ))

            # Sort actions: High -> Medium -> Low
            priority_order = {"High": 0, "Medium": 1, "Low": 2}
            actions.sort(key=lambda x: priority_order[x.priority])
            
            if actions:
                remediated_refs.append(ReferenceRemediation(
                    reference_key=ref_compliance.reference_key,
                    display_title=ref_compliance.display_title,
                    actions=actions
                ))
                
        return StudentFeedbackReport(references=remediated_refs)

    def _map_severity(self, severity: str) -> str:
        """Map validation severity to remediation priority."""
        if severity == 'error':
            return 'High'
        elif severity == 'warning':
            return 'Medium'
        return 'Low'
