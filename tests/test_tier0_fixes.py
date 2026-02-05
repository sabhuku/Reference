"""
Test Suite for Tier 0 Fixes

Tests deterministic fixes for whitespace, punctuation, year, and pages.
"""
import pytest
from src.ai_remediation.tier0_fixes import DeterministicFixer


class TestWhitespaceNormalization:
    """Test whitespace normalization."""
    
    def test_remove_extra_spaces(self):
        """Should remove extra spaces."""
        result = DeterministicFixer.normalize_whitespace("The  Great   Gatsby")
        assert result == "The Great Gatsby"
    
    def test_remove_leading_trailing_spaces(self):
        """Should remove leading/trailing spaces."""
        result = DeterministicFixer.normalize_whitespace("  Oxford University Press  ")
        assert result == "Oxford University Press"
    
    def test_handle_empty_string(self):
        """Should handle empty string."""
        result = DeterministicFixer.normalize_whitespace("")
        assert result == ""
    
    def test_handle_none(self):
        """Should handle None."""
        result = DeterministicFixer.normalize_whitespace(None)
        assert result is None


class TestPunctuationFixes:
    """Test punctuation fixes."""
    
    def test_remove_double_periods(self):
        """Should remove double periods."""
        result = DeterministicFixer.fix_double_periods("Oxford Univ. Press..")
        assert result == "Oxford Univ. Press."
    
    def test_remove_triple_periods(self):
        """Should remove triple periods."""
        result = DeterministicFixer.fix_double_periods("Vol. 5...")
        assert result == "Vol. 5."
    
    def test_remove_double_commas(self):
        """Should remove double commas."""
        result = DeterministicFixer.fix_double_commas("Smith,, John")
        assert result == "Smith, John"


class TestYearNormalization:
    """Test year normalization."""
    
    def test_remove_whitespace(self):
        """Should remove whitespace from year."""
        result = DeterministicFixer.normalize_year(" 2023 ")
        assert result == "2023"
    
    def test_remove_trailing_period(self):
        """Should remove trailing period."""
        result = DeterministicFixer.normalize_year("2023.")
        assert result == "2023"
    
    def test_valid_year_range(self):
        """Should accept valid years."""
        assert DeterministicFixer.normalize_year("2023") == "2023"
        assert DeterministicFixer.normalize_year("1999") == "1999"
        assert DeterministicFixer.normalize_year("2100") == "2100"
    
    def test_invalid_year_range(self):
        """Should reject invalid years."""
        assert DeterministicFixer.normalize_year("999") is None
        assert DeterministicFixer.normalize_year("2999") is None
    
    def test_non_numeric_year(self):
        """Should reject non-numeric years."""
        assert DeterministicFixer.normalize_year("202X") is None
        assert DeterministicFixer.normalize_year("unknown") is None


class TestPageNormalization:
    """Test page range normalization."""
    
    def test_remove_pp_prefix(self):
        """Should remove 'pp.' prefix."""
        result = DeterministicFixer.normalize_pages("pp. 123-456")
        assert result == "123-456"
    
    def test_remove_p_prefix(self):
        """Should remove 'p.' prefix."""
        result = DeterministicFixer.normalize_pages("p.123")
        assert result == "123"
    
    def test_normalize_dash_spacing(self):
        """Should normalize spaces around dash."""
        result = DeterministicFixer.normalize_pages("123 - 456")
        assert result == "123-456"
    
    def test_remove_extra_whitespace(self):
        """Should remove extra whitespace."""
        result = DeterministicFixer.normalize_pages("  123-456  ")
        assert result == "123-456"


class TestTier0Integration:
    """Test full Tier 0 fix application."""
    
    def test_apply_all_fixes(self):
        """Should apply all Tier 0 fixes."""
        reference = {
            'title': 'The  Great   Gatsby..',
            'publisher': '  Oxford University  Press  ',
            'journal': 'Nature  Biotechnology..',
            'year': ' 2023. ',
            'pages': 'pp. 123 - 456'
        }
        
        result = DeterministicFixer.apply_tier0_fixes(reference)
        
        assert len(result['patches']) == 5
        assert 'title' in result['fields_modified']
        assert 'publisher' in result['fields_modified']
        assert 'journal' in result['fields_modified']
        assert 'year' in result['fields_modified']
        assert 'pages' in result['fields_modified']
    
    def test_no_fixes_needed(self):
        """Should return empty patches if no fixes needed."""
        reference = {
            'title': 'The Great Gatsby',
            'publisher': 'Oxford University Press',
            'year': '2023'
        }
        
        result = DeterministicFixer.apply_tier0_fixes(reference)
        
        assert len(result['patches']) == 0
        assert len(result['fields_modified']) == 0
        assert 'No Tier 0 fixes needed' in result['rationale']
    
    def test_confidence_always_100(self):
        """Tier 0 fixes should always have 100% confidence."""
        reference = {
            'title': 'The  Great   Gatsby'
        }
        
        result = DeterministicFixer.apply_tier0_fixes(reference)
        
        assert result['confidence_scores']['title'] == 1.0
    
    def test_tier_is_tier_0(self):
        """Should always be tier_0."""
        reference = {
            'title': 'The  Great   Gatsby'
        }
        
        result = DeterministicFixer.apply_tier0_fixes(reference)
        
        assert result['tier'] == 'tier_0'
    
    def test_patch_format(self):
        """Patches should be RFC 6902 format."""
        reference = {
            'title': 'The  Great   Gatsby'
        }
        
        result = DeterministicFixer.apply_tier0_fixes(reference)
        
        patch = result['patches'][0]
        assert patch['op'] == 'replace'
        assert patch['path'] == '/title'
        assert patch['value'] == 'The Great Gatsby'
    
    def test_fix_details(self):
        """Should provide detailed fix information."""
        reference = {
            'title': 'The  Great   Gatsby'
        }
        
        result = DeterministicFixer.apply_tier0_fixes(reference)
        
        fix = result['fixes'][0]
        assert fix['field'] == 'title'
        assert fix['old_value'] == 'The  Great   Gatsby'
        assert fix['new_value'] == 'The Great Gatsby'
        assert fix['fix_type'] == 'whitespace_normalization'
        assert 'description' in fix


class TestDeterminism:
    """Test that fixes are deterministic."""
    
    def test_same_input_same_output(self):
        """Same input should always produce same output."""
        reference = {
            'title': 'The  Great   Gatsby..',
            'year': ' 2023. '
        }
        
        result1 = DeterministicFixer.apply_tier0_fixes(reference)
        result2 = DeterministicFixer.apply_tier0_fixes(reference)
        
        assert result1['patches'] == result2['patches']
        assert result1['fields_modified'] == result2['fields_modified']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
