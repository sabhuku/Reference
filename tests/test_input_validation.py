"""Tests for input validation functions."""
import builtins
from unittest.mock import patch

import pytest

# Import the functions we want to test
try:
    from input_validation import (
        validate_menu_choice,
        validate_author_name,
        validate_search_query,
        get_valid_input,
        confirm_action
    )
    HAS_INPUT_VALIDATION = True
except ImportError:
    # Fall back to older function names if available
    try:
        from input_validation import (
            get_valid_menu_choice as validate_menu_choice,
            get_non_empty_input as validate_author_name,
            get_non_empty_input as validate_search_query,
            get_non_empty_input as get_valid_input,
            get_user_confirmation as confirm_action,
        )
        HAS_INPUT_VALIDATION = True
    except ImportError:
        HAS_INPUT_VALIDATION = False
        
# Skip tests if input_validation module is not available
pytestmark = pytest.mark.skipif(
    not HAS_INPUT_VALIDATION,
    reason="input_validation module not found"
)

class TestValidateMenuChoice:
    """Tests for the validate_menu_choice function."""
    
    def test_valid_choice(self):
        """Test with a valid menu choice."""
        with patch('builtins.input', return_value='1'):
            result = validate_menu_choice(['1', '2', '3'], "Test prompt: ")
            assert result == '1'
    
    def test_invalid_then_valid_choice(self):
        """Test with an invalid choice followed by a valid one."""
        with patch('builtins.input', side_effect=['5', '2']):
            result = validate_menu_choice(['1', '2', '3'], "Test prompt: ")
            assert result == '2'
    
    def test_case_insensitive(self):
        """Test that choice validation is case-insensitive."""
        with patch('builtins.input', return_value='A'):
            result = validate_menu_choice(['a', 'b', 'c'], "Test prompt: ", case_sensitive=False)
            assert result == 'a'
    
    def test_case_sensitive(self):
        """Test case-sensitive choice validation."""
        with patch('builtins.input', side_effect=['a', 'A']):
            result = validate_menu_choice(['A', 'B', 'C'], "Test prompt: ", case_sensitive=True)
            assert result == 'A'

class TestValidateAuthorName:
    """Tests for the validate_author_name function."""
    
    def test_valid_author_name(self):
        """Test with a valid author name."""
        with patch('builtins.input', return_value='John Smith'):
            result = validate_author_name("Enter author name: ")
            assert result == 'John Smith'
    
    def test_empty_then_valid_name(self):
        """Test with empty input followed by valid input."""
        with patch('builtins.input', side_effect=['', 'Jane Doe']):
            result = validate_author_name("Enter author name: ")
            assert result == 'Jane Doe'
    
    def test_strip_whitespace(self):
        """Test that leading/trailing whitespace is stripped."""
        with patch('builtins.input', return_value='  John Smith  '):
            result = validate_author_name("Enter author name: ")
            assert result == 'John Smith'

class TestValidateSearchQuery:
    """Tests for the validate_search_query function."""
    
    def test_valid_search_query(self):
        """Test with a valid search query."""
        with patch('builtins.input', return_value='machine learning'):
            result = validate_search_query("Enter search query: ")
            assert result == 'machine learning'
    
    def test_empty_then_valid_query(self):
        """Test with empty input followed by valid input."""
        with patch('builtins.input', side_effect=['', 'deep learning']):
            result = validate_search_query("Enter search query: ")
            assert result == 'deep learning'
    
    def test_min_length_validation(self):
        """Test minimum length validation."""
        with patch('builtins.input', side_effect=['a', 'ab', 'abc']):
            result = validate_search_query("Enter search query: ", min_length=3)
            assert result == 'abc'

class TestGetValidInput:
    """Tests for the get_valid_input function."""
    
    def test_get_valid_input(self):
        """Test basic input validation."""
        with patch('builtins.input', return_value='test input'):
            result = get_valid_input("Enter something: ")
            assert result == 'test input'
    
    def test_validation_function(self):
        """Test with a custom validation function."""
        def is_even(s):
            return s.isdigit() and int(s) % 2 == 0
            
        with patch('builtins.input', side_effect=['3', '5', '4']):
            result = get_valid_input("Enter an even number: ", 
                                   validation_func=is_even,
                                   error_msg="Please enter an even number")
            assert result == '4'

class TestConfirmAction:
    """Tests for the confirm_action function."""
    
    def test_confirm_yes(self):
        """Test confirming with 'y' or 'yes'."""
        for response in ['y', 'Y', 'yes', 'YES', 'yEs']:
            with patch('builtins.input', return_value=response):
                assert confirm_action("Continue? ") is True
    
    def test_confirm_no(self):
        """Test not confirming with 'n' or 'no'."""
        for response in ['n', 'N', 'no', 'NO', 'nO']:
            with patch('builtins.input', return_value=response):
                assert confirm_action("Continue? ") is False
    
    def test_default_choice(self):
        """Test default choice when user just presses Enter."""
        with patch('builtins.input', return_value=''):
            # Default to True
            assert confirm_action("Continue? ", default=True) is True
            # Default to False
            assert confirm_action("Continue? ", default=False) is False
    
    def test_invalid_then_valid_input(self):
        """Test with invalid input followed by valid input."""
        with patch('builtins.input', side_effect=['maybe', 'y']):
            assert confirm_action("Continue? ") is True
