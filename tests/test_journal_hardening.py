"""
Unit Tests for Journal Classification Hardening

Tests the corrective hardening implementation that addresses:
1. Confidence preservation (no forging)
2. Robust year detection (parentheses OR standalone)
3. Guarded journal name matching (requires pages/DOI)
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelling.pipeline import predict_stage1, harden_journal_classification, load_stage1_model

# Check if model is available
MODEL_AVAILABLE = load_stage1_model() is not None

if not MODEL_AVAILABLE:
    print("WARNING: ML model not available. Testing hardening function directly.")
    print()


def test_journal_with_pages_no_volume():
    """Journal + year + pages, no volume → should classify as journal"""
    ref = "Smith, J. (2020) 'Article Title', Nature, pp. 123-456."
    
    if MODEL_AVAILABLE:
        result = predict_stage1(ref)
    else:
        # Test hardening function directly
        mock_ml = {"predicted_type": "unknown", "type_confidence": 0.5}
        result = harden_journal_classification(ref, mock_ml)
    
    assert result["predicted_type"] == "journal", f"Expected 'journal', got '{result['predicted_type']}'"
    print("+ Test 1 PASS: Journal with pages (no volume) classified correctly")


def test_journal_with_doi_no_volume():
    """Journal + year + DOI, no volume → should classify as journal"""
    ref = "Jones, A. (2021) 'Study', Science. doi:10.1234/science.abc123"
    
    if MODEL_AVAILABLE:
        result = predict_stage1(ref)
    else:
        mock_ml = {"predicted_type": "unknown", "type_confidence": 0.5}
        result = harden_journal_classification(ref, mock_ml)
    
    assert result["predicted_type"] == "journal", f"Expected 'journal', got '{result['predicted_type']}'"
    print("+ Test 2 PASS: Journal with DOI (no volume) classified correctly")


def test_ssrn_with_doi_remains_non_journal():
    """SSRN with DOI → should NOT be classified as journal"""
    ref = "Brown, B. (2022) 'Paper', SSRN. doi:10.2139/ssrn.123456"
    
    if MODEL_AVAILABLE:
        result = predict_stage1(ref)
    else:
        mock_ml = {"predicted_type": "unknown", "type_confidence": 0.5}
        result = harden_journal_classification(ref, mock_ml)
    
    assert result["predicted_type"] != "journal", f"SSRN should not be 'journal', got '{result['predicted_type']}'"
    print("+ Test 3 PASS: SSRN correctly excluded from journal classification")


def test_existing_journal_unchanged():
    """Fully-specified journal → ML classification unchanged"""
    ref = "Hochreiter, S. and Schmidhuber, J. (1997) 'Long short-term memory', Neural Computation, 9(8), pp.1735-1780."
    result = predict_stage1(ref)
    assert result["predicted_type"] == "journal", f"Expected 'journal', got '{result['predicted_type']}'"
    print("+ Test 4 PASS: Fully-specified journal classified correctly")


def test_book_not_affected():
    """Book reference → should not be classified as journal"""
    ref = "Author, A. (2020) Book Title. New York: Publisher."
    result = predict_stage1(ref)
    assert result["predicted_type"] != "journal", f"Book should not be 'journal', got '{result['predicted_type']}'"
    print("+ Test 5 PASS: Book not misclassified as journal")


# CORRECTIVE TESTS (addressing the 3 issues)

def test_confidence_preserved_not_forged():
    """CRITICAL: Confidence must be preserved from ML, not forged"""
    ref = "Smith, J. (2020) 'Title', Journal Name, pp. 100-200."
    
    # Mock ML output with low confidence
    mock_ml_output = {"predicted_type": "unknown", "type_confidence": 0.45}
    
    # Apply hardening
    result = harden_journal_classification(ref, mock_ml_output)
    
    # Confidence MUST be preserved (0.45), not forged (e.g., 0.76)
    assert result["type_confidence"] == 0.45, \
        f"Confidence forging detected! Expected 0.45, got {result['type_confidence']}"
    assert result["predicted_type"] == "journal", \
        f"Expected hardening to apply, got '{result['predicted_type']}'"
    
    print("+ Test 6 PASS: Confidence preserved (not forged)")


def test_standalone_year_detection():
    """Year detection must work for standalone years (not just parentheses)"""
    # Year without parentheses
    ref1 = "Author, A. 2020. 'Title', Journal, pp. 10-20."
    result1 = predict_stage1(ref1)
    
    # Year with parentheses
    ref2 = "Author, B. (2021) 'Title', Journal, pp. 30-40."
    result2 = predict_stage1(ref2)
    
    # Both should be classified as journal
    assert result1["predicted_type"] == "journal", \
        f"Standalone year not detected! Got '{result1['predicted_type']}'"
    assert result2["predicted_type"] == "journal", \
        f"Parenthesized year not detected! Got '{result2['predicted_type']}'"
    
    print("+ Test 7 PASS: Both standalone and parenthesized years detected")


def test_journal_name_requires_pages_or_doi():
    """Journal name alone is insufficient - must have pages OR DOI"""
    # Journal name + year, but NO pages or DOI → should NOT be journal
    ref = "Author, C. (2022) 'Title', Some Journal Name."
    result = predict_stage1(ref)
    
    assert result["predicted_type"] != "journal", \
        f"Journal name without pages/DOI should not trigger hardening, got '{result['predicted_type']}'"
    
    print("+ Test 8 PASS: Journal name alone does not trigger hardening")


def test_book_with_year_not_misclassified():
    """Books with years should not be misclassified as journals"""
    ref = "Author, D. (2023) Book Title. Publisher."
    result = predict_stage1(ref)
    
    assert result["predicted_type"] != "journal", \
        f"Book should not be journal, got '{result['predicted_type']}'"
    
    print("+ Test 9 PASS: Book with year not misclassified")


def test_preprint_repositories_excluded():
    """All preprint repositories must be excluded"""
    repos = ["SSRN", "arXiv", "bioRxiv", "medRxiv", "PsyArXiv", "SocArXiv"]
    
    for repo in repos:
        ref = f"Author, E. (2024) 'Paper', {repo}, pp. 1-10. doi:10.1234/test"
        result = predict_stage1(ref)
        
        assert result["predicted_type"] != "journal", \
            f"{repo} should be excluded, got '{result['predicted_type']}'"
    
    print("+ Test 10 PASS: All preprint repositories excluded")


def test_real_world_example_1():
    """Real-world example: Journal article missing volume"""
    ref = "Chasakara, R. and Maseka, N. (2021) 'Fishing for administrative justice in marine spatial planning', Journal of Ocean Governance in Africa, pp. 122-146."
    result = predict_stage1(ref)
    
    assert result["predicted_type"] == "journal", \
        f"Real-world journal should be classified, got '{result['predicted_type']}'"
    
    print("+ Test 11 PASS: Real-world example classified correctly")


def test_real_world_example_2():
    """Real-world example: Journal with DOI, no volume"""
    ref = "Maseka, N. (2023) 'Marine spatial planning', Ocean Studies. doi:10.47348/joga/2023/a1"
    result = predict_stage1(ref)
    
    assert result["predicted_type"] == "journal", \
        f"Journal with DOI should be classified, got '{result['predicted_type']}'"
    
    print("+ Test 12 PASS: Journal with DOI classified correctly")


if __name__ == "__main__":
    print("=" * 70)
    print("JOURNAL CLASSIFICATION HARDENING - UNIT TESTS")
    print("=" * 70)
    print()
    
    tests = [
        test_journal_with_pages_no_volume,
        test_journal_with_doi_no_volume,
        test_ssrn_with_doi_remains_non_journal,
        test_existing_journal_unchanged,
        test_book_not_affected,
        test_confidence_preserved_not_forged,
        test_standalone_year_detection,
        test_journal_name_requires_pages_or_doi,
        test_book_with_year_not_misclassified,
        test_preprint_repositories_excluded,
        test_real_world_example_1,
        test_real_world_example_2,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"X {test.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"X {test.__name__} ERROR: {e}")
            failed += 1
    
    print()
    print("=" * 70)
    print(f"RESULTS: {passed}/{len(tests)} tests passed")
    if failed > 0:
        print(f"WARNING: {failed} test(s) failed")
    else:
        print("SUCCESS: All tests passed!")
    print("=" * 70)
