"""
Reference Assistant - Core functionality
"""
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Set

import requests
from docx import Document

from .api import CrossRefAPI, GoogleBooksAPI
from .config import Config
from .models import Publication
from .utils.input_validation import InputValidator
from .utils.logging_setup import setup_logging, log_operation

class ReferenceManager:
    def __init__(self):
        self.config = Config()
        self.refs: List[Publication] = []
        self.sources: Set[str] = set()
        self.style = self.config.DEFAULT_STYLE
        self.cache = self._load_cache()
        
        # Initialize APIs
        self.crossref = CrossRefAPI(self.config.CROSSREF_MAILTO)
        self.google_books = GoogleBooksAPI(self.config.GOOGLE_BOOKS_API_KEY)
        
        # Set up logging
        setup_logging()
        
        # Initialize actions
        from .actions import ReferenceManagerActions
        self.actions = ReferenceManagerActions(self)
        
    # Delegate action methods to the actions instance
    def action_search_single(self) -> None:
        self.actions.action_search_single()
    
    def action_search_author(self) -> None:
        self.actions.action_search_author()
    
    def action_view_current(self) -> None:
        self.actions.action_view_current()
    
    def action_view_citations(self) -> None:
        self.actions.action_view_citations()
    
    def action_change_style(self) -> None:
        self.actions.action_change_style()
    
    def action_export_and_exit(self) -> bool:
        return self.actions.action_export_and_exit()
        
    def _load_cache(self) -> Dict:
        """Load cache from file."""
        if os.path.exists(self.config.CACHE_FILE):
            try:
                with open(self.config.CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Error loading cache: {e}")
                return {}
        return {}
    
    def _save_cache(self) -> None:
        """Save cache to file."""
        try:
            from dataclasses import asdict, is_dataclass
            
            # Helper to convert dataclasses to dicts recursively
            class EnhancedJSONEncoder(json.JSONEncoder):
                def default(self, o):
                    if is_dataclass(o):
                        return asdict(o)
                    return super().default(o)
                    
            with open(self.config.CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False, cls=EnhancedJSONEncoder)
        except Exception as e:
            logging.error(f"Error saving cache: {e}")
    
    def search_single_work(self, query: str) -> Optional[Publication]:
        """Search for a single work."""
        key = f"query:{query}"
        if key in self.cache:
            return self.cache[key]
        
        try:
            # Check for DOI
            if query.startswith("10.") or "doi.org" in query:
                meta = self.crossref.search_doi(query)
                if meta:
                    self.cache[key] = meta
                    self._save_cache()
                    return meta

            if self._looks_booky(query):
                meta = (self.google_books.search_single(query) or 
                       self.crossref.search_single(query))
            else:
                meta = (self.crossref.search_single(query) or 
                       self.google_books.search_single(query))
            
            if meta:
                self.cache[key] = meta
                self._save_cache()
            return meta
        except Exception as e:
            logging.error(f"Error searching for work: {e}")
            return None
    
    def search_author_works(self, author: str) -> List[Publication]:
        """Search for works by an author."""
        key = f"author:{author}"
        if key in self.cache and self.cache[key]:
            return self.cache[key]
        
        try:
            works_crossref = self.crossref.search_author(author) or []
            works_gb = self.google_books.search_author(author) or []
            
            # Combine results
            works = works_crossref + works_gb
            
            if works:
                self.cache[key] = works
                self._save_cache()
            return works
        except Exception as e:
            logging.error(f"Error searching for author works: {e}")
            return []
    
    @staticmethod
    def _looks_booky(query: str) -> bool:
        """Check if query looks like a book search."""
        qlow = query.lower()
        words = query.split()
        if len(words) <= 5:
            return True
        for w in ["handbook", "introduction", "foundations", "press", "textbook"]:
            if w in qlow:
                return True
        return False