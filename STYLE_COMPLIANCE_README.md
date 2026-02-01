# Style Compliance Subsystem (Harvard v1)

## Overview

This subsystem provides automated validation of bibliography references against a conservative Harvard style specification. It is designed to assist both markers (by highlighting potential errors) and students (by providing constructive feedback), while strictly maintaining a separation of concerns.

## Subsystem Boundaries

### Marker Context vs. Student Context

The system operates in two distinct modes, enforced by separate components:

1.  **Marker Context (Compliance Report)**
    *   **Component**: `src.style.reporter.HarvardComplianceReporter`
    *   **Purpose**: Audit and Assessment support.
    *   **Output**: Strict, data-centric report with rule IDs (e.g., `HARVARD.AUTHOR.MISSING`), severity classifications (Error/Warning/Info), and an advisory compliance score (0-100).
    *   **Tone**: Neutral, objective, diagnostic.

2.  **Student Context (Remediation Feedback)**
    *   **Component**: `src.style.remediation.RemediationGenerator`
    *   **Purpose**: Formative learning and self-correction.
    *   **Output**: Actionable, prioritized suggestions (High/Medium/Low).
    *   **Tone**: Supportive, instructional, non-judgemental.
    *   **Constraints**: Never reveals the raw "score" or uses penalizing language.

## Ruleset Versioning

*   **Current Version**: `harvard_v1`
*   **Status**: **FROZEN**
*   **Specification**: See `harvard_rules_spec.md` (internal artifact).
*   **Scope**: Covers 10 conservative, defensible rules applicable to general UK thesis marking. It avoids institutional micro-variants (e.g., specific punctuation defaults) to remain broadly applicable.

## Non-Goals & Limitations

*   **No Automated Grading**: The "Compliance Score" is purely advisory and statistical. It **must not** be used as a final grade without academic review.
*   **No Institutional Guarantees**: This system checks against a generic "defensible Harvard" standard. It does not guarantee compliance with specific departmental style guides that may deviate from standard practices.
*   **No Auto-Correction**: The system identifies issues but does not attempt to rewrite references automatically. This preserves student agency and academic integrity.
