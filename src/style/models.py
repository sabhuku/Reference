"""Data models for reference style compliance."""
from dataclasses import dataclass, field
from typing import List, Literal, Optional

Severity = Literal['error', 'warning', 'info']

@dataclass
class Violation:
    """Represents a single rule violation in a reference."""
    rule_id: str
    severity: Severity
    message: str
    field_name: Optional[str] = None
    reference_id: Optional[str] = None

@dataclass
class ReferenceMetadata:
    """Minimal metadata for a reference required for reporting."""
    id: str
    display_title: str
    formatted_ref: Optional[str] = None
    provenance: Optional[dict] = None

@dataclass
class ReferenceCompliance:
    """Compliance details for a single reference."""
    reference_key: str
    display_title: str # Used for UI, but normalized_reference is the full string
    normalised_reference: str
    compliance_score: float
    violations: List[Violation] = field(default_factory=list)
    provenance: Optional[dict] = None # Added for tracking inferred fields
    
    @property
    def has_errors(self) -> bool:
        return any(v.severity == 'error' for v in self.violations)

@dataclass
class ComplianceStats:
    """Aggregate statistics for a compliance report."""
    errors: int = 0
    warnings: int = 0
    suggestions: int = 0
    # Backward compatibility aliases/helpers if needed
    @property
    def error_count(self): return self.errors
    @property
    def warning_count(self): return self.warnings
    @property
    def info_count(self): return self.suggestions

@dataclass
class ComplianceReport:
    """Full compliance report for a bibliography."""
    overall_compliance_score: float
    summary: str # marker_summary
    counts: ComplianceStats # stats
    references: List[ReferenceCompliance] # details
    style: str = "Harvard"
    style_version: Optional[str] = None
    
    # Aliases for backward compatibility with UI templates
    @property
    def overall_score(self): return self.overall_compliance_score
    @property
    def marker_summary(self): return self.summary
    @property
    def stats(self): return self.counts
    @property
    def details(self): return self.references
