
import json
import os
import joblib
import warnings
from typing import Dict, Any, Optional

# Import Stages
try:
    from stage2_orchestrator import run_stage2
    from stage3_remediator import remediate_reference
except ImportError:
    # Fallback for relative imports
    from modelling.stage2_orchestrator import run_stage2
    from modelling.stage3_remediator import remediate_reference

# Global Model Cache
_STAGE1_MODEL = None

def load_stage1_model():
    """Lazily loads the calibrated Stage 1 classifier."""
    global _STAGE1_MODEL
    if _STAGE1_MODEL is None:
        # Path relative to this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(current_dir, "stage1_reference_classifier_calibrated.pkl")
        try:
             _STAGE1_MODEL = joblib.load(model_path)
        except Exception as e:
             # If model missing (e.g. in minimal test env), return None
             # Real app should raise
             warnings.warn(f"Stage 1 model could not be loaded: {e}")
             return None
    return _STAGE1_MODEL

def harden_journal_classification(raw_reference: str, ml_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic fallback for journal article classification.
    
    Applies structural rules when ML classifier misses journal articles
    due to missing volume information.
    
    CRITICAL: Preserves original ML confidence - does NOT forge confidence values.
    
    Args:
        raw_reference: The raw reference string
        ml_output: Output from ML classifier (confidence preserved)
        
    Returns:
        Hardened classification output (may override type, preserves confidence)
    """
    import re
    
    # If already classified as journal, return unchanged
    if ml_output.get("predicted_type", "").lower() == "journal":
        return ml_output
    
    ref_lower = raw_reference.lower()
    
    # SAFEGUARD 1: Exclude preprint repositories
    preprint_repos = ["ssrn", "arxiv", "biorxiv", "medrxiv", "psyarxiv", "socarxiv"]
    if any(repo in ref_lower for repo in preprint_repos):
        return ml_output
    
    # STRUCTURAL SIGNAL DETECTION
    
    # 1. Year Detection (strengthened - allows parentheses OR standalone)
    year_pattern = r'\b(19\d{2}|20\d{2})\b'
    year_match = re.search(year_pattern, raw_reference)
    has_year = year_match is not None
    
    # 2. Page Range Detection (required for journal validation)
    page_pattern = r'pp?\.\s*(\d+)[-–](\d+)'
    page_match = re.search(page_pattern, raw_reference)
    has_page_range = page_match is not None
    
    # 3. DOI Detection (alternative to pages)
    doi_pattern = r'10\.\d{4,}/[^\s]+'
    doi_match = re.search(doi_pattern, raw_reference)
    has_doi = doi_match is not None
    
    # 4. Journal Name Detection (GUARDED - only valid with pages/DOI)
    # Look for text that could be a journal name (capitalized text before volume/year/pages)
    # This is intentionally broad but MUST be validated by pages/DOI presence
    journal_pattern = r'[A-Z][^(,]+?(?=\s*(?:\d+\(|\(|\s+pp?\.|,\s*pp?\.|$))'
    journal_match = re.search(journal_pattern, raw_reference)
    has_journal_candidate = journal_match is not None
    
    # FALLBACK RULE (with guarded journal detection)
    # Journal name is ONLY considered valid if pages OR DOI are present
    has_valid_journal = has_journal_candidate and (has_page_range or has_doi)
    
    if has_valid_journal and has_year and (has_page_range or has_doi):
        # Apply hardening: override type, PRESERVE confidence
        return {
            "predicted_type": "journal",
            "type_confidence": ml_output.get("type_confidence", 0.0),  # PRESERVED
            "hardening_applied": True  # For debugging/logging
        }
    
    # No hardening applied
    return ml_output

def predict_stage1(raw_reference: str) -> Dict[str, Any]:
    """Wraps Stage 1 Model Prediction with deterministic hardening."""
    model = load_stage1_model()
    
    if model:
        # Model expects list/iterable
        try:
            probas = model.predict_proba([raw_reference])[0]
            classes = model.classes_
            
            # Get max confidence and class
            max_idx = probas.argmax()
            confidence = float(probas[max_idx])
            pred_type = str(classes[max_idx])
            
            ml_output = {
                "predicted_type": pred_type,
                "type_confidence": confidence
            }
            
            # Apply deterministic hardening (preserves confidence)
            hardened_output = harden_journal_classification(raw_reference, ml_output)
            return hardened_output
            
        except Exception as e:
            # Fallback for model error
            return {"predicted_type": "unknown", "type_confidence": 0.0}
    else:
        # Mock/Fallback if model file missing
        return {"predicted_type": "unknown", "type_confidence": 0.0}

def run_pipeline(raw_reference: str, _mock_stage1_output: Optional[Dict] = None, analysis_mode: bool = False) -> Dict[str, Any]:
    """
    Phase 4 Orchestration Pipeline.
    Integrates Stage 1 (Classify), Stage 2 (Extract), and Stage 3 (Remediate).
    
    Args:
        raw_reference: The reference string.
        _mock_stage1_output: For testing only. Overrides Stage 1 prediction.
        analysis_mode: If True, Stage 3 is NEVER executed (passive reporting only).
                      Prevents external API calls and generative remediation.
        
    Returns:
        Full pipeline envelope.
    """
    
    # 1. Stage 1 Execution & Gate
    if _mock_stage1_output:
        stage1_out = _mock_stage1_output
    else:
        stage1_out = predict_stage1(raw_reference)
        
    pred_type = stage1_out.get("predicted_type", "unknown")
    confidence = stage1_out.get("type_confidence", 0.0)
    
    # Gate: Unknown or Low Confidence
    if pred_type == "unknown" or confidence < 0.75:
        return {
            "raw_reference": raw_reference,
            "reference_type": pred_type,
            "type_confidence": confidence,
            "stage2": None,
            "stage3": None,
            "pipeline_status": "rejected_stage1"
        }

    # 2. Stage 2 Execution
    # Pass Stage 1 output into Stage 2 Orchestrator
    # Note: run_stage2 expects {predicted_type, type_confidence} in stage1_output
    stage2_result = run_stage2(raw_reference, stage1_out)
    
    # 3. Stage 3 Conditional Invocation
    stage3_result = None
    
    s2_status = stage2_result.get("extraction_status", "failed")
    
    if s2_status == "complete":
        # SKIP Stage 3 describes intent: Deterministic layer was sufficient
        pass
    elif analysis_mode:
        # ANALYSIS MODE: Stage 3 is DISABLED for passive reporting
        # No external API calls or generative remediation
        stage3_result = {
            "status": "skipped_analysis_mode",
            "message": "Stage 3 disabled in analysis mode (passive reporting)"
        }
    else:
        # CALL Stage 3
        # Construct input envelope for Stage 3
        s3_input = {
            "raw_reference": raw_reference,
            "reference_type": pred_type,
            "stage2_output": stage2_result
        }
        stage3_result = remediate_reference(s3_input)
        
        # 🛑 SAFETY ASSERTION
        if stage3_result:
             assert stage3_result["requires_review"] is True, "Safety Violation: Stage 3 output must require review."

    # 4. Final Output Assembly
    return {
        "raw_reference": raw_reference,
        "reference_type": pred_type,
        "type_confidence": confidence,
        "stage2": stage2_result,
        "stage3": stage3_result,
        "pipeline_status": "success"
    }

# --- TEST CASES ---
if __name__ == "__main__":
    print("--- Phase 4 Pipeline Orchestration Tests ---\n")
    
    # Test 1: Stage 2 Complete -> Stage 3 Skipped
    print("Test 1: Stage 2 Complete (Mock)")
    mock_s1_complete = {"predicted_type": "journal", "type_confidence": 0.95}
    # Mock Stage 2 to return complete (we rely on run_stage2 logic, so we need a good string or force it?)
    # Since we import run_stage2, we can't easily mock it without patching.
    # However, we can pass a string known to be perfect for the Journal Extractor.
    # Recalling Verification: "Hochreiter, S. and Schmidhuber, J. (1997) ..."
    # That produced partial authors before fix, but now should produce complete logic?
    # Actually, Stage 2 Orchestrator returns 'complete' if req_fields are >= 0.8
    # Let's use a mocked stage1 output and a known good string.
    
    # Actually, to strictly test *Orchestration* irrespective of Extractor quality, 
    # we ideally mock `run_stage2`. But here we are integrating.
    # Let's use a string that we know works:
    # "Hochreiter, S. and Schmidhuber, J. (1997) 'Long short-term memory', Neural Computation, 9(8), pp.1735-1780." 
    # This returned good scores in our pilot.
    
    ref_complete = "Hochreiter, S. and Schmidhuber, J. (1997) 'Long short-term memory', Neural Computation, 9(8), pp.1735-1780."
    res1 = run_pipeline(ref_complete, _mock_stage1_output=mock_s1_complete)
    
    print(f"S2 Status: {res1['stage2']['extraction_status']}")
    print(f"Stage 3: {res1['stage3']}") # Should be None or Skipped logic (Stage 3 returned skipped dict in previous step? No, `run_pipeline` conditional logic says SKIP)
    # Wait, my logic above: if s2_status == "complete": pass (so stage3_result remains None)
    # The output format requires "stage3": { ... } | null
    # So None is correct.
    
    # Test 2: Stage 2 Partial -> Stage 3 Invoked
    print("\nTest 2: Stage 2 Partial")
    mock_s1_partial = {"predicted_type": "website", "type_confidence": 0.85}
    # Website with missing fields
    ref_partial = "Google (2020) Search Engine. https://google.com" 
    res2 = run_pipeline(ref_partial, _mock_stage1_output=mock_s1_partial)
    
    print(f"S2 Status: {res2['stage2']['extraction_status']}")
    print(f"Stage 3 Invoked: {res2['stage3'] is not None}")
    if res2['stage3']:
         print(f"Stage 3 Review Flag: {res2['stage3']['requires_review']}")

    # Test 3: Stage 1 Rejected -> Skipped
    print("\nTest 3: Stage 1 Rejected")
    mock_s1_reject = {"predicted_type": "unknown", "type_confidence": 0.0}
    ref_reject = "Garbage..."
    res3 = run_pipeline(ref_reject, _mock_stage1_output=mock_s1_reject)
    
    print(f"Pipeline Status: {res3['pipeline_status']}")
    print(f"Stage 2: {res3['stage2']}")
    print(f"Stage 3: {res3['stage3']}")
    
    print("-" * 40)
