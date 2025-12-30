from abc import ABC, abstractmethod
from typing import List, Set, Dict
from custom_types import Publication

class Command(ABC):
    @abstractmethod
    def execute(self) -> None:
        pass

class SearchSingleCommand(Command):
    def __init__(self, refs: List[Publication], cache: Dict, sources: Set[str], style: str):
        self.refs = refs
        self.cache = cache
        self.sources = sources
        self.style = style
    
    def execute(self) -> None:
        from referencing import action_search_single
        action_search_single(self.refs, self.cache, self.sources, self.style)

class SearchAuthorCommand(Command):
    def __init__(self, refs: List[Publication], cache: Dict, sources: Set[str], style: str):
        self.refs = refs
        self.cache = cache
        self.sources = sources
        self.style = style
    
    def execute(self) -> None:
        from referencing import action_search_author
        action_search_author(self.refs, self.cache, self.sources, self.style)

# Add more command classes for other menu options...