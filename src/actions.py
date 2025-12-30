"""Action methods for the ReferenceManager class."""
from typing import List, Optional

from .utils.error_handling import user_input_handler
from .utils.input_validation import InputValidator
from .models import Publication

class ReferenceManagerActions:
    """Action methods for handling user interactions."""
    
    def __init__(self, manager):
        self.manager = manager
        self.validator = InputValidator()
    
    @user_input_handler
    def action_search_single(self) -> None:
        """Handle search by title/book."""
        query = self.validator.get_search_query("Enter title or keywords: ")
        if not query:
            return
            
        work = self.manager.search_single_work(query)
        if not work:
            print("No match found.")
            return
            
        self.manager.sources.add(work.source)
        
        # Show preview
        print("\nIn-text:", self.manager.in_text_citation(work))
        print("Full ref:", self.manager.reference_entry(work))
        
        # Confirm addition
        if self.validator.confirm_action("Add this to bibliography?"):
            self.manager.refs.append(work)
            print("Added.")
    
    @user_input_handler
    def action_search_author(self) -> None:
        """Handle search by author."""
        author = self.validator.get_author_name("Enter author name: ")
        if not author:
            return
            
        works = self.manager.search_author_works(author)
        if not works:
            print("No works found.")
            return
            
        for work in works:
            self.manager.sources.add(work.source)
        
        while True:
            print(f"\nWorks for {author}:")
            for i, work in enumerate(works, 1):
                j = work.journal or work.publisher
                print(f"{i}. {work.title} ({work.year}) — {j}")
                
            numbers = input("Select numbers (comma) or Enter to finish: ").strip()
            if not numbers:
                break
                
            for num in numbers.split(","):
                if num.strip().isdigit():
                    idx = int(num.strip())
                    if 1 <= idx <= len(works):
                        chosen = works[idx-1]
                        self.manager.refs.append(chosen)
                        print("Added:")
                        print("  In-text:", self.manager.in_text_citation(chosen))
                        print("  Ref   :", self.manager.reference_entry(chosen))
                    else:
                        print(f"Ignored {num}: out of range.")
    
    @user_input_handler
    def action_view_current(self) -> None:
        """Show current bibliography."""
        uniq = self.manager.dedupe()
        if not uniq:
            print("\n(No items yet.)")
            return
            
        refs_sorted = self.manager.sort_for_bibliography(uniq)
        print("\nCurrent bibliography:")
        for idx, work in enumerate(refs_sorted, 1):
            print(f"{idx}. {self.manager.reference_entry(work)}")
    
    @user_input_handler
    def action_view_citations(self) -> None:
        """Show citations and references."""
        uniq = self.manager.dedupe()
        if not uniq:
            print("\n(No items yet.)")
            return
            
        refs_sorted = self.manager.sort_for_bibliography(uniq)
        print("\nCitations and references:")
        for idx, work in enumerate(refs_sorted, 1):
            print(f"[{idx}] In-text: {self.manager.in_text_citation(work)}")
            print(f"     Ref   : {self.manager.reference_entry(work)}")
            print("")
    
    @user_input_handler
    def action_change_style(self) -> None:
        """Change reference style."""
        print("\nChoose style:")
        print("1. Harvard")
        print("2. APA")
        print("3. IEEE")
        
        choice = self.validator.get_menu_choice(1, 3)
        if choice == 1:
            self.manager.style = self.manager.config.STYLE_HARVARD
        elif choice == 2:
            self.manager.style = self.manager.config.STYLE_APA
        elif choice == 3:
            self.manager.style = self.manager.config.STYLE_IEEE
        else:
            print("Keeping previous style.")
    
    @user_input_handler
    def action_export_and_exit(self) -> bool:
        """Export bibliography and exit."""
        uniq = self.manager.dedupe()
        if not uniq:
            print("Nothing to save.")
            return True
            
        refs_sorted = self.manager.sort_for_bibliography(uniq)
        path = self.manager.save_references_to_word(refs_sorted)
        print("Saved to:", path)
        return True