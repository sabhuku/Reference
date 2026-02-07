# Stage 3 Reviewer / UI Contract

**Status:** APPROVED (Refined)
**Scope:** Stage 3 Assistive Generative Remediation

## 1. Visual Separation

### Stage 2: Deterministic Extraction (Authoritative)
*   **Visual Style:** Standard/Primary text color (e.g., Black/Dark Grey).
*   **Border/Background:** None or Standard Input styling.
*   **Label:** "Extracted" (Tooltip: "Deterministically extracted from source").
*   **Read-Only:** Yes (by default, requires explicit "Edit" action to override).

### Stage 3: Generative Suggestion (Advisory)
*   **Visual Style:** Muted/Italicized text or distintive suggestion color (e.g., Amber/Blue tint).
*   **Border/Background:** Dashed border or light amber background warning.
*   **Label:** ⚠️ **"Suggested — requires review"** (Must be prominent).
*   **Confidence Indicator:**
    *   Display numeric confidence (e.g., "55%").
    *   Visual bar/color code (Orange for 0.4-0.6, Red for <0.4).
*   **Placement:** Must appear *below* or *alongside* the empty field, never pre-filled as if final.

### Refinement: Empty State (No Suggestion)
*   **Condition:** Stage 3 produces no candidates for a partial/failed field.
*   **Visual Style:** Muted/Grey text within the suggestion area.
*   **Content:** "No safe suggestions available for this field."
*   **Purpose:** Reinforce omission-over-guessing; prevents user assuming system failed silently.

### Refinement: Review Indicator
*   **Element:** Non-dismissible badge or icon (e.g., 🔴 or ⚠️).
*   **Content:** "Review Required".
*   **Visibility:** Persistent on the record header/card if `requires_review = true`.
*   **Behavior:** Cannot be hidden or dismissed until explicit reviewer action is taken on all flagged fields.

## 2. Reviewer Actions

### Allowed Actions
1.  **Accept Suggestion:**
    *   Action: Click "Accept" / "Use this".
    *   Effect: Copies suggestion value into the final field.
    *   State Change: `status` becomes `manual_review`, `reviewer_id` recorded.
2.  **Edit Suggestion:**
    *   Action: Click "Edit".
    *   Effect: Populates input with suggestion text, allows modification.
    *   State Change: `status` becomes `manual_edit`.
3.  **Reject/Ignore:**
    *   Action: Click "Discard" or leave field empty.
    *   Effect: Suggestion is dismissed, field remains empty.

### Forbidden Actions
1.  **Batch Accept:** "Accept All Suggestions" button is **STRICTLY PROHIBITED**.
2.  **Implicit Acceptance:** Saving the record without interacting with the suggestion must **NOT** auto-accept it. The field must remain empty/failed.
3.  **Hiding Source:** Reviewers must always be able to see the `raw_reference` string while reviewing Stage 3 suggestions.

## 3. Audit Logging

### Required Metadata
Every interaction must create an audit log entry containing:

| Field | Description |
| :--- | :--- |
| `timestamp` | UTC timestamp of action. |
| `reference_id` | Unique ID of the reference. |
| `user_id` | ID of the human reviewer. |
| `field_name` | The field being modified (e.g., `authors`). |
| `action_type` | See below. |
| `original_value` | The value proposed by Stage 3 (or Stage 2 if overriding). |
| `stage_confidence` | The confidence score of the source. |
| `final_value` | The actual value saved to the database. |

### Decision Types & Refinements

1.  **Stage 3 Interactions:**
    *   `accept_suggestion`: `final_value` == `original_suggestion`
    *   `edit_suggestion`: `final_value` != `original_suggestion` (Levenshtein > 0)
    *   `reject_suggestion`: Suggestion dismissed.

2.  **Refinement: Stage 2 Manual Overrides**
    *   **Scope:** Any modification to a deterministically extracted (Stage 2) field.
    *   **Action Type:** `manual_override`.
    *   **Requirement:** Must explicitly log the `original_extracted_value` (from Stage 2) alongside the `final_value` to trace divergence from ground truth.
