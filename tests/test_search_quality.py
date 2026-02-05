import unittest
from unittest.mock import MagicMock, patch
from src.reference_manager import ReferenceManager
from src.models import Publication

class TestSearchQuality(unittest.TestCase):
    def setUp(self):
        self.manager = ReferenceManager()
        # Mock dependencies if necessary, but we are primarily testing _rank_results 
        # which is a pure pure-ish function (logic wise)

    def _make_pub(self, title, doi="10.1000/test"):
        """Helper to create a dummy publication."""
        return Publication(
            title=title,
            authors=["Smith"],
            year="2020",
            doi=doi,
            source="crossref",
            pub_type="article",
            journal="",
            publisher="",
            location="",
            volume="",
            issue="",
            pages=""
        )

    def test_stopword_filtering(self):
        """
        Verify that stopwords don't trigger false positives.
        Query: "Let's do mathematics"
        Should NOT match: "Let us pray" (matches "let", "us"?) -> "Let" is stopword? 
        If 'let' and 'do' are stopwords, only 'mathematics' remains.
        """
        # "Let's do mathematics" -> stopwords: "let", "do" (if in list). 
        # "mathematics" remains.
        
        # Scenario: Title "Let It Be" vs Query "Let's do mathematics"
        # If "let" is stopword, no match.
        
        p1 = self._make_pub("Let It Be")
        p2 = self._make_pub("Advanced Mathematics")
        
        results = self.manager._rank_results([(p1, 'crossref'), (p2, 'crossref')], "Let's do mathematics")
        
        # p2 should be ranked higher or p1 should be dropped/scored very low
        p1_score = next((r.confidence_score for r in results if r.title == "Let It Be"), 0)
        p2_score = next((r.confidence_score for r in results if r.title == "Advanced Mathematics"), 0)
        
        self.assertLess(p1_score, p2_score, "Stopwords should not drive high relevance")
        self.assertLess(p1_score, 20, "Irrelevant match on stopwords should have low score")

    def test_proximity_scoring(self):
        """
        Verify that adjacent keywords score higher than distant ones.
        Query: "A-level Mathematics"
        """
        # Pub 1: "A-level Mathematics content" (Adjacent)
        p1 = self._make_pub("A-level Mathematics content")
        
        # Pub 2: "Multi-level Deep Learning for Mathematics" (Distant)
        p2 = self._make_pub("Multi-level Deep Learning for Mathematics")
        
        results = self.manager._rank_results([(p1, 'crossref'), (p2, 'crossref')], "A-level Mathematics")
        
        r1 = next((r for r in results if r.title == p1.title), None)
        r2 = next((r for r in results if r.title == p2.title), None)
        
        self.assertIsNotNone(r1, "Relevant proximity result should be kept")
        
        if r2:
            print(f"Proximity Test: {p1.title} ({r1.confidence_score}) vs {p2.title} ({r2.confidence_score})")
            self.assertGreater(r1.confidence_score, r2.confidence_score, "Adjacent keywords should score higher")
        else:
            print(f"Proximity Test: Distant match '{p2.title}' correctly dropped.")

    def test_phrase_aware_matching_diverse(self):
        """
        Verify phrase-aware matching across diverse subjects.
        """
        test_cases = [
            # (Query, Good Title, Bad Title)
            ("A'level Biology", "Plant Biology (Top 9) Higher Level", "Complexity in Systems Level Biology"),
            ("A-level History", "A-level History: The Cold War", "History of Sea Level Rise"),
            ("A-level Law", "A-level Law Textbook", "High-level legal frameworks for AI"),
            ("A-level Mathematics", "Pure Mathematics A-Level", "Multi-level modeling in Mathematics")
        ]
        
        for query, good_title, bad_title in test_cases:
            with self.subTest(query=query):
                p_good = self._make_pub(good_title)
                p_bad = self._make_pub(bad_title)
                
                results = self.manager._rank_results([(p_good, 'crossref'), (p_bad, 'crossref')], query)
                
                # Check if bad result is dropped or scored significantly lower
                good_res = next((r for r in results if r.title == good_title), None)
                bad_res = next((r for r in results if r.title == bad_title), None)
                
                self.assertIsNotNone(good_res, f"Relevant result '{good_title}' should be kept")
                
                if bad_res:
                    print(f"Phrase Test '{query}': Good={good_res.confidence_score}, Bad={bad_res.confidence_score}")
                    self.assertGreater(good_res.confidence_score, bad_res.confidence_score + 20, 
                                      f"Educational phrase mismatch for '{bad_title}' should be penalized heavily")
                else:
                    print(f"Phrase Test '{query}': Bad result '{bad_title}' correctly dropped.")

    def test_search_mode_strictness(self):
        """
        Verify that 'title' mode is stricter than 'general' mode.
        """
        query = "systems biology"
        # A title that contains keywords but is fuzzy/partial in a way that might pass general but fail strict
        # Actually, let's use a case where keywords match but it's not a "Title" match per se 
        # (simulating the backend drop logic for low fuzzy scores in title mode)
        
        p = self._make_pub("Introduction to Biological Systems") # Contains "systems" and "biological" (~biology)
        
        # General Mode
        res_general = self.manager._rank_results([(p, 'crossref')], query, search_mode='general')
        self.assertTrue(len(res_general) > 0, "General mode should match keywords fuzzy")
        
        # Title Mode
        # "systems biology" vs "Introduction to Biological Systems" -> Ratio is likely < 80 and not exact
        # And no educational phrase. Should be dropped or scored very low.
        res_title = self.manager._rank_results([(p, 'crossref')], query, search_mode='title')
        
        if res_title:
             print(f"Title Mode Score: {res_title[0].confidence_score}")
             # If it survives, it better be because the fuzzy match was actually surprisingly high
             # But we expect the strict logic to filter "mid" matches
             self.assertTrue(res_title[0].confidence_score < res_general[0].confidence_score, 
                             "Title mode should be stricter/lower score for non-exact matches")
        else:
            print("Title Mode correctly dropped fuzzy match.")

if __name__ == '__main__':
    unittest.main()
