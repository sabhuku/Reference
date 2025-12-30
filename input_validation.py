from typing import Optional

def get_valid_menu_choice(min_choice: int = 1, max_choice: int = 7) -> int:
    """Get and validate user menu choice."""
    while True:
        choice = input(f"Choice ({min_choice}-{max_choice}): ").strip()
        if choice.isdigit():
            num = int(choice)
            if min_choice <= num <= max_choice:
                return num
        print(f"Please enter a number between {min_choice} and {max_choice}")

def get_user_confirmation(prompt: str) -> bool:
    """Get yes/no confirmation from user."""
    while True:
        response = input(f"{prompt} (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        if response in ['n', 'no']:
            return False
        print("Please answer 'y' or 'n'")

def get_non_empty_input(prompt: str) -> str:
    """Get non-empty input from user."""
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Please enter a non-empty value")