
import json
import logging
from typing import Dict, Any, Optional

# Import Extractors
# Assuming these are in the same package/directory. If run as script, needs path handling.
try:
    from stage2_journal_extractor import extract_journal_fields
    from stage2_book_extractor import extract_book_fields
    from stage2_website_extractor import extract_website_fields
except ImportError:
    # Fallback for running as script from parent dir or testing context
    try:
        from modelling.stage2_journal_extractor import extract_journal_fields
        from modelling.stage2_book_extractor import extract_book_fields
        from modelling.stage2_website_extractor import extract_website_fields
    except ImportError:
         pass # Allow test case runner to handle mocks if needed or fail later

def run_stage2(raw_reference: str, stage1_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Orchestrates Stage 2 extraction based on Stage 1 classification.
    
    Args:
        raw_reference: The reference string.
        stage1_output: Dict containing 'predicted_type' and 'type_confidence'.
        
    Returns:
        Stage 2 envelope.
    """
    predicted_type = stage1_output.get("predicted_type", "unknown")
    type_confidence = stage1_output.get("type_confidence", 0.0)
    
    # 1. Stage 1 Confidence Gate
    # IF predicted_type == "unknown" OR type_confidence < 0.75 -> 'failed'
    if predicted_type == "unknown" or type_confidence < 0.75:
        return {
            "raw_reference": raw_reference,
            "reference_type": predicted_type,
            "type_confidence": type_confidence,
            "extraction_status": "failed",
            "fields": {},
            "metadata": {
                "extractor_version": "stage2_v1",
                "routing_notes": [f"Gated by Stage 1 confidence ({type_confidence}) or unknown type"]
            }
        }

    # 2. Extractor Routing
    extractor_func = None
    if predicted_type == "journal":
        extractor_func = extract_journal_fields
    elif predicted_type == "book":
        extractor_func = extract_book_fields
    elif predicted_type == "website":
        extractor_func = extract_website_fields
    
    if not extractor_func:
        return {
            "raw_reference": raw_reference,
            "reference_type": predicted_type,
            "type_confidence": type_confidence,
            "extraction_status": "not_implemented",
            "fields": {},
            "metadata": {
                "extractor_version": "stage2_v1",
                "routing_notes": [f"No extractor for type: {predicted_type}"]
            }
        }

    # Execute Extraction with Error Handling
    try:
        extractor_result = extractor_func(raw_reference)
        
        # 3. Output Assembly
        # Start with base envelope structure
        envelope = {
            "raw_reference": raw_reference,
            "reference_type": predicted_type,
            "type_confidence": type_confidence,
            # Inherit status and fields from extractor result
            "extraction_status": extractor_result.get("extraction_status", "failed"),
            "fields": extractor_result.get("fields", {}),
            "metadata": extractor_result.get("metadata", {})
        }
        
        # Ensure metadata has required fields
        if "extractor_version" not in envelope["metadata"]:
             envelope["metadata"]["extractor_version"] = "stage2_v1"
        if "routing_notes" not in envelope["metadata"]:
             envelope["metadata"]["routing_notes"] = []
             
        # Add routing note
        envelope["metadata"]["routing_notes"].append(f"Routed to {predicted_type} extractor")

        return envelope

    except Exception as e:
        # Catch-all for extractor errors
        return {
            "raw_reference": raw_reference,
            "reference_type": predicted_type,
            "type_confidence": type_confidence,
            "extraction_status": "failed",
            "fields": {},
            "metadata": {
                "extractor_version": "stage2_v1",
                "routing_notes": [f"Exception during extraction: {str(e)}"]
            }
        }

# TEST CASES
if __name__ == "__main__":
    # Mock extractors if imports failed (for standalone testing without actual extractor files present in path)
    if 'extract_journal_fields' not in globals():
        def extract_journal_fields(ref):
             return {"extraction_status": "complete", "fields": {"year": 2020}, "metadata": {}}
        def extract_book_fields(ref):
             return {"extraction_status": "complete", "fields": {}, "metadata": {}}
        def extract_website_fields(ref):
             return {"extraction_status": "partial", "fields": {"url": "http://..."}, "metadata": {}}

    print("--- Stage 2 Orchestration Tests ---\n")

    # Test Case 1: High-confidence journal -> complete extraction
    print("Test 1: High-confidence journal")
    input_1 = {
        "raw_reference": "Hochreiter, S. (1997) 'LSTM', Neural Comp, 9(8).",
        "stage1_output": {"predicted_type": "journal", "type_confidence": 0.95}
    }
    # Note: real extraction depends on raw string content. 
    # If using real extractors, this string might produce partial/failed if regex doesn't match perfectly unless the string is perfect.
    # For the purpose of testing *orchestration*, we check the routing and envelope structure.
    # To get "complete" from real extractor, we need a good string.
    # Using a known good string from previous context.
    input_1["raw_reference"] = "Hochreiter, S. and Schmidhuber, J. (1997) 'Long short-term memory', Neural Computation, 9(8), pp.1735-1780." 
    
    result_1 = run_stage2(input_1["raw_reference"], input_1["stage1_output"])
    print(json.dumps(result_1, indent=2, default=str))
    print("-" * 20)

    # Test Case 2: High-confidence website -> partial extraction
    print("\nTest 2: High-confidence website (Partial)")
    input_2 = {
        "raw_reference": "OpenAI (2023) ChatGPT. Available at: https://openai.com",
        "stage1_output": {"predicted_type": "website", "type_confidence": 0.88}
    }
    result_2 = run_stage2(input_2["raw_reference"], input_2["stage1_output"])
    print(json.dumps(result_2, indent=2, default=str))
    print("-" * 20)

    # Test Case 3: Low-confidence Stage 1 input -> no extraction attempted
    print("\nTest 3: Low-confidence Input")
    input_3 = {
        "raw_reference": "Ambiguous text string...",
        "stage1_output": {"predicted_type": "custom", "type_confidence": 0.45}
    }
    result_3 = run_stage2(input_3["raw_reference"], input_3["stage1_output"])
    print(json.dumps(result_3, indent=2, default=str))
    print("-" * 20)
