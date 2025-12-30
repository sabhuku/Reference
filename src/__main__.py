"""Main entry point for the reference manager."""
import logging
from typing import NoReturn

from .reference_manager import ReferenceManager
from .utils.input_validation import InputValidator
from .utils.logging_setup import setup_logging, log_operation

def main() -> NoReturn:
    """Main program entry point."""
    # Set up logging
    setup_logging()
    
    try:
        # Initialize reference manager
        manager = ReferenceManager()
        validator = InputValidator()
        
        logging.info("Reference Assistant started")
        print("===== Reference Assistant =====")
        print(f"Saving to: {manager.config.DOWNLOAD_FOLDER}/{manager.config.WORD_FILENAME}")
        print(f"Cache file: {manager.config.CACHE_FILE}")
        print(f"Initial style: {manager.style.upper()}")
        
        while True:
            print("\nMenu:")
            print(f"1. Search by title/book (current style: {manager.style.upper()})")
            print(f"2. Search by author (current style: {manager.style.upper()})")
            print("3. View current bibliography")
            print("4. Export & exit")
            print("5. Exit without saving")
            print("6. Change reference style")
            print("7. Show citations for current list")
            
            choice = validator.get_menu_choice()
            if not choice:
                continue
                
            if choice == 1:
                manager.action_search_single()
            elif choice == 2:
                manager.action_search_author()
            elif choice == 3:
                manager.action_view_current()
            elif choice == 4:
                if manager.action_export_and_exit():
                    break
            elif choice == 5:
                print("Exiting without saving.")
                break
            elif choice == 6:
                manager.action_change_style()
            elif choice == 7:
                manager.action_view_citations()
                
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        print("An unexpected error occurred. Check the logs for details.")
    finally:
        logging.info("Reference Assistant finished")

if __name__ == "__main__":
    main()