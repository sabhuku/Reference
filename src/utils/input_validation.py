"""Input validation utilities."""
import re
from typing import Any, Callable, Optional

from .error_handling import user_input_handler

class InputValidator:
    """Input validation and user interaction."""
    
    @staticmethod
    @user_input_handler
    def get_menu_choice(min_val: int = 1, max_val: int = 7) -> Optional[int]:
        """Get and validate menu choice from user."""
        choice = input(f"Choice ({min_val}-{max_val}): ").strip()
        if choice.isdigit():
            num = int(choice)
            if min_val <= num <= max_val:
                return num
        print(f"Please enter a number between {min_val} and {max_val}")
        return None
    
    @staticmethod
    @user_input_handler
    def get_search_query(prompt: str) -> Optional[str]:
        """Get and validate search query."""
        query = input(prompt).strip()
        if len(query) < 3:
            print("Search query must be at least 3 characters long")
            return None
        return query
    
    @staticmethod
    @user_input_handler
    def get_author_name(prompt: str) -> Optional[str]:
        """Get and validate author name."""
        name = input(prompt).strip()
        if len(name) < 2:
            print("Author name must be at least 2 characters long")
            return None
        # Remove special characters except spaces and hyphens
        return re.sub(r'[^\w\s-]', '', name)
    
    @staticmethod
    @user_input_handler
    def confirm_action(prompt: str) -> bool:
        """Get yes/no confirmation from user."""
        response = input(f"{prompt} (y/n): ").strip().lower()
        return response in ['y', 'yes']
    
    @staticmethod
    def get_valid_input(prompt: str, validator: Callable[[str], Any], 
                       error_msg: str) -> Optional[Any]:
        """Get valid input with retry logic."""
        while True:
            user_input = input(prompt).strip()
            if user_input.lower() == 'q':
                return None
            result = validator(user_input)
            if result is not None:
                return result
            print(f"{error_msg} (Press 'q' to cancel)")