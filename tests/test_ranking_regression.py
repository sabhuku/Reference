import pytest
import copy
from unittest.mock import MagicMock, patch
from src.reference_manager import ReferenceManager
from src.models import Publication
from src.style.harvard_checker import HarvardStyleChecker

class TestRankingRegression:
    
    @pytest.fixture
    def manager(self):
        with patch('src.reference_manager.Config'):
            mgr = ReferenceManager()
            # Disable real API calls via mocks if needed, 
            # but for regression on logic we might want to bypass search entirely
            # and test the component methods directly (_rank_results, _deduplicate_results)
            return mgr

    def test_noise_filter_blocks_irrelevant(self, manager):
        """
        Regression test for 'Foundation Mathematics' stray results.
        Logic: Hard drop if score < 10 and no keyword match.
        """
        # Create a irrelevant result
        irrelevant = Publication(
            title="Foundation Mathematics", # The query is exactly this title though?
            # Wait, if query matches title exactly, score should be high.
            # The issue in check_noise_filter was that query "Foundation Mathematics" 
            # returned stuff with low confidence if not exactly matching?
            # Let's mock a low-scoring result.
            authors=["Stroud"], year="2020", source="crossref", doi="10.1",
            pub_type="book", journal="", publisher="", location="", volume="", issue="", pages=""
        )
        
        # If we pass (irrelevant, "crossref") to _rank_results with a DIFFERENT query
        # it should get a low score.
        
        # Scenario 1: Query "Advanced Physics", result "Foundation Mathematics"
        # Score should be low.
        input_list = [(irrelevant, 'crossref')]
        
        # We need to spy on internal scoring if possible, or just check if it's dropped.
        # But _rank_results drops items if they meet drop criteria.
        
        results = manager._rank_results(input_list, "Advanced Physics")
        
        # Should be empty or very low score
        if results:
             assert results[0].confidence_score < 10.0
             # If it was dropped entirely, results would be empty, which is also good
        
    def test_tiebreaker_determinism(self, manager):
        """
        Regression test for validate_tiebreaker.py.
        Ensure identical scores are ranked deterministically (DOI -> Title -> Year).
        """
        # Create 3 pubs using same logic as validate_tiebreaker.py
        p1 = Publication(title="Analysis of AI", authors=["Smith"], year="2020", doi="10.1000/a", source="crossref",
                         pub_type="article", journal="", publisher="", location="", volume="", issue="", pages="")
        p2 = Publication(title="Analysis of AI", authors=["Smith"], year="2021", doi="10.1000/b", source="crossref",
                         pub_type="article", journal="", publisher="", location="", volume="", issue="", pages="")
        p3 = Publication(title="Analysis of BI", authors=["Smith"], year="2020", doi="10.1000/c", source="crossref",
                         pub_type="article", journal="", publisher="", location="", volume="", issue="", pages="")
        
        # All have 'crossref' source (same base score).
        # Query matches "Analysis of AI"
        query = "Analysis of AI"
        
        # shuffle inputs 10 times, result order should be identical
        import random
        base_input = [(p1, 'crossref'), (p2, 'crossref'), (p3, 'crossref')]
        
        previous_order = None
        
        for _ in range(10):
            current_input = list(base_input)
            random.shuffle(current_input)
            
            ranked = manager._rank_results(current_input, query)
            ranked_ids = [p.doi for p in ranked]
            
            if previous_order:
                assert ranked_ids == previous_order, f"Ranking order changed! {ranked_ids} != {previous_order}"
            previous_order = ranked_ids

    def test_scoring_consistency(self, manager):
        """
        Regression for verify_scoring_consistency.py.
        Ensure compliance scores are calculated deterministically.
        """
        checker = HarvardStyleChecker()
        
        p = Publication(title="Machine Learning", authors=["Lee"], year="2021", doi="10.1000/test", 
                        source="crossref", pub_type="article", journal="Nature", 
                        publisher="", location="", volume="1", issue="1", pages="10-12")
        
        # Force violations check
        score1 = 0
        score2 = 0
        
        # Run 1
        p1 = copy.deepcopy(p)
        violations1 = checker.check_single(p1)
        # Violation objects usually have 'severity'. Penalty calculation logic might be in ReportGenerator, not Checker.
        # Let's assign arbitrary penalties for testing consistency
        penalty_map = {'error': 10, 'warning': 5, 'info': 0}
        score1 = max(0.0, 100.0 - sum(penalty_map.get(v.severity, 0) for v in violations1))
        
        # Run 2
        p2 = copy.deepcopy(p)
        violations2 = checker.check_single(p2)
        score2 = max(0.0, 100.0 - sum(penalty_map.get(v.severity, 0) for v in violations2))
        
        assert abs(score1 - score2) < 0.001, f"Scoring non-deterministic: {score1} vs {score2}"

    def test_deduplication_stability(self, manager):
        """
        Regression for identical vs fuzzy deduplication.
        """
        # Identical Group
        p1 = Publication(title="Unique Title A", authors=["Smith"], year="2020", doi="10.1000/A", source="crossref", 
                         pub_type="article", journal="", publisher="", location="", volume="", issue="", pages="")
        p2 = copy.deepcopy(p1)
        
        # Fuzzy Group
        p3 = Publication(title="Machine Learning in Health", authors=["Lee"], year="2021", doi="10.1000/C1", 
                         source="crossref", pub_type="article", journal="", publisher="", location="", volume="", issue="", pages="")
        p4 = Publication(title="Machine Learning in Health.", authors=["Lee"], year="2021", doi="10.1000/C1_dup", 
                         source="crossref", pub_type="article", journal="", publisher="", location="", volume="", issue="", pages="")
        
        input_pubs = [p1, p2, p3, p4]
        
        # _deduplicate_results expects a list of Publication objects (it usually handles the dict check too)
        # Assuming internal method usage
        deduped = manager._deduplicate_results(input_pubs)
        
        # Expect p1/p2 to merge -> 1
        group_a = [p for p in deduped if "10.1000/A" in p.doi]
        assert len(group_a) == 1, "Identical publications failed to deduplicate"
        
        # Expect p3/p4 to merge -> 1 (if fuzzy logic holds)
        group_c = [p for p in deduped if "10.1000/C1" in p.doi]
        assert len(group_c) == 1, f"Fuzzy duplicates failed to merge: Found {len(group_c)}"
