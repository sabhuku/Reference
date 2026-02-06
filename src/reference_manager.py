"""
Reference Assistant - Core functionality

This module provides the ReferenceManager class which orchestrates
reference search, storage, and compliance operations.

ARCHITECTURE NOTES (v2.0 - Project-Scoped):
- References are stored in Project objects, NOT in this class
- All operations require explicit project_id (no hidden state)
- Only "default" project is auto-created
- Precedence: explicit publications parameter overrides project storage
"""
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from fuzzywuzzy import fuzz

import requests
import re
from docx import Document

from .api import CrossRefAPI, GoogleBooksAPI, PubMedAPI
from .config import Config
from .models import Publication
from .project_manager import ProjectManager, ProjectNotFoundError
from .utils.input_validation import InputValidator
from .utils.logging_setup import setup_logging, log_operation
from .style.reporter import HarvardComplianceReporter
from .style.remediation import RemediationGenerator

class ReferenceManager:
    """
    Orchestrates reference search, storage, and compliance operations.
    
    ARCHITECTURE (v2.0 - Project-Scoped):
    - NO global reference list (removed self.refs)
    - References stored in Project objects via ProjectManager
    - All operations require explicit project_id parameter
    - Only "default" project is auto-created
    - No hidden state (_current_project_id removed)
    
    PRECEDENCE RULE for check_style_compliance:
    - IF publications parameter provided → use it (ignore project storage)
    - IF publications is None → use project.get_references()
    """
    
    DEFAULT_PROJECT_ID = "default"
    
    def __init__(self, project_manager: Optional[ProjectManager] = None):
        """
        Initialize ReferenceManager.
        
        Args:
            project_manager: Optional ProjectManager instance.
                            If None, creates new one with default storage path.
        """
        self.config = Config()
        
        # PROJECT-SCOPED STORAGE (replaces self.refs)
        self._project_manager = project_manager or ProjectManager(
            storage_path=os.path.join(
                os.path.dirname(self.config.CACHE_FILE) or '.',
                'projects.json'
            )
        )
        
        # DEPRECATED: self.refs is removed
        # For backward compatibility, provide a property that accesses default project
        
        self.sources: Set[str] = set()
        self.style = self.config.DEFAULT_STYLE
        
        # Lazy cache initialization (for search results, not reference storage)
        self._cache = None
        import threading
        self._cache_lock = threading.RLock()
        
        # Initialize APIs
        self.crossref = CrossRefAPI(self.config.CROSSREF_MAILTO)
        self.google_books = GoogleBooksAPI(self.config.GOOGLE_BOOKS_API_KEY)
        self.pubmed = PubMedAPI()
        
        # Set up logging
        setup_logging()
        
        # Initialize actions
        from .actions import ReferenceManagerActions
        self.actions = ReferenceManagerActions(self)
    
    # =========================================================================
    # NOTE: self.refs REMOVED (v2.1)
    # =========================================================================
    # The deprecated self.refs property has been intentionally removed.
    #
    # REASON: Shallow copy exposed internal Publication objects, allowing
    # external mutation that could contaminate project state.
    #
    # MIGRATION: Replace all uses of self.refs with explicit project API:
    #   OLD: manager.refs                     → NEW: manager.get_project_references("default")
    #   OLD: manager.refs.append(pub)         → NEW: manager.add_reference_to_project(pub)
    #   OLD: manager.refs = [pub1, pub2]      → NEW: See set_project_references() below
    #   OLD: len(manager.refs)                → NEW: manager.get_project_reference_count()
    # =========================================================================
    
    def set_project_references(
        self,
        publications: List[Publication],
        project_id: str = "default"
    ) -> None:
        """
        Replace all references in a project with new list.
        
        This replaces the deprecated self.refs = [...] pattern.
        
        Args:
            publications: New list of publications
            project_id: Target project ID
        
        Raises:
            ProjectNotFoundError: If project doesn't exist (except "default")
        """
        project = self._project_manager.get_or_create_project(project_id)
        project.clear_references()
        for pub in publications:
            project.add_reference(pub)
    
    # =========================================================================
    # PROJECT-SCOPED REFERENCE OPERATIONS
    # =========================================================================
    
    def add_reference_to_project(
        self,
        pub: Publication,
        project_id: str = "default"
    ) -> None:
        """
        Add a reference to a specific project.
        
        Args:
            pub: Publication to add
            project_id: Target project ID (default: "default")
        
        Raises:
            ProjectNotFoundError: If project doesn't exist (except "default")
            TypeError: If pub is not a Publication
        """
        project = self._project_manager.get_or_create_project(project_id)
        project.add_reference(pub)
    
    def remove_reference_from_project(
        self,
        pub: Publication,
        project_id: str = "default"
    ) -> bool:
        """
        Remove a reference from a specific project.
        
        Args:
            pub: Publication to remove
            project_id: Target project ID (default: "default")
        
        Returns:
            True if removed, False if not found
        
        Raises:
            ProjectNotFoundError: If project doesn't exist
        """
        project = self._project_manager.get_or_create_project(project_id)
        return project.remove_reference(pub)
    
    def get_project_references(self, project_id: str = "default") -> List[Publication]:
        """
        Get all references from a project.
        
        Returns a deep copy by default for full isolation.
        External mutations will NOT affect project state.
        
        Args:
            project_id: Project ID (default: "default")
        
        Returns:
            List of Publication objects (deep copy)
        
        Raises:
            ProjectNotFoundError: If project doesn't exist
        """
        project = self._project_manager.get_or_create_project(project_id)
        return project.get_references()  # deep=True by default
    
    def clear_project_references(self, project_id: str = "default") -> None:
        """
        Remove all references from a project.
        
        Args:
            project_id: Project ID (default: "default")
        
        Raises:
            ProjectNotFoundError: If project doesn't exist
        """
        project = self._project_manager.get_or_create_project(project_id)
        project.clear_references()
    
    def get_project_reference_count(self, project_id: str = "default") -> int:
        """
        Get number of references in a project.
        
        Args:
            project_id: Project ID (default: "default")
        
        Returns:
            Number of references
        
        Raises:
            ProjectNotFoundError: If project doesn't exist
        """
        project = self._project_manager.get_or_create_project(project_id)
        return project.reference_count()
    
    # =========================================================================
    # PROJECT MANAGER ACCESS
    # =========================================================================
    
    @property
    def project_manager(self) -> ProjectManager:
        """Access the underlying ProjectManager."""
        return self._project_manager
    
    def save_projects(self) -> None:
        """Save all projects to persistent storage."""
        self._project_manager.save()
    
    def load_projects(self) -> None:
        """Load all projects from persistent storage."""
        self._project_manager.load()
    
    @property
    def cache(self) -> Dict:
        """Lazy load cache in a thread-safe manner."""
        if self._cache is None:
            with self._cache_lock:
                if self._cache is None:
                    self._cache = self._load_cache()
        return self._cache

    @cache.setter
    def cache(self, value):
        with self._cache_lock:
            self._cache = value
        
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
        
    def check_style_compliance(
        self,
        publications: Optional[List[Publication]] = None,
        project_id: str = "default"
    ) -> Dict:
        """
        Run compliance checks and generate student feedback.
        
        PRECEDENCE RULE:
        - IF publications is provided → use it (ignore project storage)
        - IF publications is None → use project.get_references()
        
        Args:
            publications: Optional explicit list of publications to check.
                         If provided, project storage is ignored.
            project_id: Project to use if publications is None.
                       Only "default" is auto-created.
        
        Returns:
            Dict with 'report', 'feedback', and 'results' keys
        
        Raises:
            ProjectNotFoundError: If project doesn't exist and publications is None
        """
        # PRECEDENCE RULE: explicit publications override project storage
        if publications is not None:
            refs_to_check = publications
        else:
            project = self._project_manager.get_or_create_project(project_id)
            refs_to_check = project.get_references()
        
        # Processing logic UNCHANGED from original
        from .style.reporter import HarvardComplianceReporter
        from .style.remediation import RemediationGenerator
        
        reporter = HarvardComplianceReporter()
        report = reporter.generate_report(refs_to_check)
        
        remediator = RemediationGenerator()
        feedback = remediator.generate(report)
        
        # Create a lookup for feedback
        feedback_map = {item.reference_key: item for item in feedback.references}
        
        # Merge for UI
        merged_results = []
        for ref in report.references:
            fb = feedback_map.get(ref.reference_key)
            merged_results.append({
                'reference_key': ref.reference_key,
                'display_title': ref.display_title,
                'compliance_score': ref.compliance_score,
                'violations': ref.violations,
                'actions': fb.actions if fb else [],
                'provenance': ref.provenance
            })
        
        # Sort by score (ascending) then by reference_key for determinism
        merged_results.sort(key=lambda x: (x['compliance_score'], x['reference_key']))
        
        return {
            "report": report,
            "feedback": feedback,
            "results": merged_results
        }

    def parse_reference(self, raw_text: str) -> Publication:
        """
        Parse a raw reference string using the Phase 4 Pipeline (Stage 1-3).
        
        Args:
            raw_text: The raw reference string.
            
        Returns:
            Publication object with populated fields and remediation data if applicable.
        """
        # Import here to avoid circular dependencies
        try:
            from modelling.pipeline import run_pipeline
        except ImportError:
            # Fallback for when running from src directory
            import sys
            import os
            sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
            from modelling.pipeline import run_pipeline

        # Run pipeline
        result = run_pipeline(raw_text)
        
        # Convert pipeline result to Publication
        # We need to map extracted fields to Publication fields
        
        s2 = result.get("stage2") or {}
        s2_fields = s2.get("fields", {})
        
        # Helper to extract value from field dict
        def get_val(f): return s2_fields.get(f, {}).get("value")
        
        # Infer type mapping
        pipeline_type = result.get("reference_type", "unknown")
        
        # Map common fields
        pub = Publication(
            source="pipeline_extraction",
            pub_type=pipeline_type,
            authors=get_val("authors") or [],
            year=str(get_val("year") or ""),
            title=str(get_val("title") or ""),
            journal=str(get_val("journal") or ""),
            publisher=str(get_val("publisher") or ""),
            location=str(get_val("location") or ""),
            volume=str(get_val("volume") or ""),
            issue=str(get_val("issue") or ""),
            pages=str(get_val("pages") or ""),
            doi=str(get_val("doi") or ""),
            url=str(get_val("url") or ""),
            match_type="extraction",
            confidence_score=result.get("type_confidence", 0.0)
        )
        
        # Attach remediation data if present
        s3 = result.get("stage3")
        if s3:
            pub.remediation = s3
            pub.review_required = s3.get("requires_review", False)
            
        return pub
        
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
        """Save cache to file atomically."""
        import copy
        import tempfile
        import shutil
        
        try:
            from dataclasses import asdict, is_dataclass
            
            # Helper to convert dataclasses to dicts recursively
            class EnhancedJSONEncoder(json.JSONEncoder):
                def default(self, o):
                    if is_dataclass(o):
                        return asdict(o)
                    return super().default(o)
            
            # Acquire lock to ensure thread safety
            with self._cache_lock:
                # Defensive deep copy to prevent concurrent modification during serialization
                # Note: copy.deepcopy can be expensive but ensures snapshot consistency
                cache_snapshot = copy.deepcopy(self.cache)
                
                # Write to temporary file first
                # Use delete=False so we can rename it later (Windows requirement for atomic replace)
                with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False) as tf:
                    json.dump(cache_snapshot, tf, indent=2, ensure_ascii=False, cls=EnhancedJSONEncoder)
                    tf.flush()
                    os.fsync(tf.fileno()) # Force write to disk
                    temp_path = tf.name
                
                # Atomic replace
                shutil.move(temp_path, self.config.CACHE_FILE)
                    
        except Exception as e:
            logging.error(f"Error saving cache: {e}")
            # Try to cleanup temp file if it exists and wasn't moved
            try:
                if 'temp_path' in locals() and os.path.exists(temp_path):
                    os.remove(temp_path)
            except:
                pass
    
    def search_single_work(self, query: str, use_parallel: bool = True) -> Optional[Publication]:
        """Search for a single work."""
        key = f"query:{query}"
        if key in self.cache:
            entry = self.cache[key]
            # Check if entry is new format (dict with 'timestamp' and 'data')
            is_new_format = isinstance(entry, dict) and 'timestamp' in entry and 'data' in entry
            
            valid = True
            if is_new_format:
                import time
                # Default TTL: 7 days (604800 seconds)
                ttl = getattr(self.config, 'CACHE_TTL', 604800)
                if time.time() - entry['timestamp'] > ttl:
                    logging.info(f"Cache expired for: {query}")
                    del self.cache[key]
                    valid = False
                else:
                    data = entry['data']
            else:
                # Legacy format: raw data, assume valid or migrate?
                # Let's treat legacy as valid but maybe ideally we'd timestamp it now?
                # For backward compatibility, treat as valid.
                data = entry
                
            if valid:
                logging.info(f"Cache hit for: {query}")
                import copy
                res = copy.deepcopy(data)
                
                if hasattr(res, 'retrieval_method'):
                     res.retrieval_method = 'cache'
                elif isinstance(res, dict):
                     res['retrieval_method'] = 'cache'
                     
                return res
        
        try:
            # Check for DOI first (fast path)
            if query.startswith("10.") or "doi.org" in query:
                meta = self.crossref.search_doi(query)
                if meta:
                    import copy
                    import time
                    # Store DEEP COPY in cache with timestamp
                    self.cache[key] = {
                        'timestamp': time.time(),
                        'data': copy.deepcopy(meta)
                    }
                    self._save_cache()
                    # Return DEEP COPY to caller
                    return copy.deepcopy(meta)
            
            # Use parallel search for better performance
            if use_parallel:
                logging.info(f"Using parallel search for: {query}")
                results = self.parallel_search(query)
                meta = results[0] if results else None
            else:
                # Fall back to sequential search
                logging.info(f"Using sequential search for: {query}")
                if self._looks_booky(query):
                    meta = (self.google_books.search_single(query) or 
                           self.crossref.search_single(query) or
                           self.pubmed.search_single(query))
                else:
                    meta = (self.crossref.search_single(query) or
                           self.pubmed.search_single(query) or 
                           self.google_books.search_single(query))
            
            if meta:
                # Attach metadata
                meta.retrieval_method = "api_sequential"
                meta.match_type = "single_best"
                meta.confidence_score = 0.95
                if not hasattr(meta, 'source'):
                    meta.source = 'unknown_single'
                
                # Author ambiguity default
                if not hasattr(meta, 'author_ambiguity'):
                     meta.author_ambiguity = 0.0

                import copy
                import time
                self.cache[key] = {
                    'timestamp': time.time(),
                    'data': copy.deepcopy(meta)
                }
                self._save_cache()
            return copy.deepcopy(meta)
    
        except Exception as e:
            logging.error(f"Error searching for work: {e}")
            return None

    def search_works(self, query: str, limit: int = 5, search_mode: str = 'general', **kwargs) -> List[Publication]:
        """Search for works and return a ranked list."""
        # For now, just use parallel search
        return self.parallel_search(query, limit, search_mode=search_mode, **kwargs)
    
    def search_author_works(self, author: str, **kwargs) -> List[Publication]:
        """Search for works by an author."""
        
        # Create a cache key that includes filter parameters
        # Sort keys to ensure stable cache key
        filter_key = sorted([(k, str(v)) for k, v in kwargs.items() if v])
        key = f"author:{author}:{filter_key}"
        
        if key in self.cache:
            entry = self.cache[key]
            is_new_format = isinstance(entry, dict) and 'timestamp' in entry and 'data' in entry
            
            valid = True
            if is_new_format:
                import time
                ttl = getattr(self.config, 'CACHE_TTL', 604800)
                if time.time() - entry['timestamp'] > ttl:
                    logging.info(f"Cache expired for: {key}")
                    del self.cache[key]
                    valid = False
                else:
                    data = entry['data']
            else:
                data = entry
                
            if valid and data:
                import copy
                cached_results = copy.deepcopy(data)
                
                # Check if we need to re-hydrate dicts to Publications 
                hydrated_results = []
                for res in cached_results:
                     if isinstance(res, dict):
                         # Re-hydrate
                         try:
                             # Extract internal fields not in init
                             mt = res.pop('match_type', 'fuzzy')
                             conf = res.pop('confidence_score', 0.0)
                             rm = res.pop('retrieval_method', 'cache')
                             n_auth = res.pop('normalized_authors', [])
                             auth_inf = res.pop('authors_inferred', False)
                             y_stat = res.pop('year_status', 'present')
                             s_inf = res.pop('source_type_inferred', False)
                             n_log = res.pop('normalization_log', [])
                             
                             # Some fields might be missing from older caches or slightly different
                             # Filter keys to only those in Publication.__init__
                             import inspect
                             init_params = inspect.signature(Publication.__init__).parameters
                             clean_kwargs = {k: v for k, v in res.items() if k in init_params and k != 'self'}
                             
                             pub = Publication(**clean_kwargs)
                             
                             # Restore internal extras
                             pub.match_type = mt
                             pub.confidence_score = conf
                             pub.retrieval_method = rm
                             pub.normalized_authors = n_auth
                             pub.authors_inferred = auth_inf
                             pub.year_status = y_stat
                             pub.source_type_inferred = s_inf
                             pub.normalization_log = n_log
                             
                             hydrated_results.append(pub)
                         except Exception as e:
                             logging.warning(f"Failed to rehydrate cached publication: {e}")
                     else:
                         if hasattr(res, 'retrieval_method'):
                            res.retrieval_method = 'cache'
                         hydrated_results.append(res)
                         
                return hydrated_results
        
        try:
            works_crossref = self.crossref.search_author(author) or []
            works_pubmed = self.pubmed.search_author(author) or []
            works_gb = self.google_books.search_author(author) or []
            
            # Combine results
            works = works_crossref + works_pubmed + works_gb
            
            # Post-filtering: Verify valid author match to remove irrelevant results
            # (Especially needed for PubMed which can be loose)
            from .name_utils import names_match, guess_first_last_from_author_query
            
            target_first, target_last = guess_first_last_from_author_query(author)
            
            # Prepare swapped variant for robust matching
            # If query is "Ruvinga Stenford", target_first=Ruvinga, target_last=Stenford
            # We want to check against "Stenford Ruvinga" too.
            should_check_swapped = False
            if target_first and target_last:
                 should_check_swapped = True
            
            filtered_works = []
            for work in works:
                match_found = False
                # Works should have 'authors' list
                authors_list = work.authors if isinstance(work.authors, list) else str(work.authors).split(', ')
                
                for auth_str in authors_list:
                    # auth_str is typically "Surname, Given" or "Given Surname" depending on source parser
                    # We need to robustly parse it.
                    # Our parsers usually output "Surname, Given" or just Name.
                    
                    # Simple heuristic parser for the author string from the work
                    if "," in auth_str:
                         parts = auth_str.split(",", 1)
                         family = parts[0].strip()
                         given = parts[1].strip()
                    else:
                         parts = auth_str.split()
                         if len(parts) >= 2:
                             family = parts[-1]
                             given = " ".join(parts[:-1])
                         else:
                             family = auth_str
                             given = ""
                             
                    if names_match(target_first, target_last, given, family):
                        match_found = True
                        break
                        
                    # Check swapped variant if applicable
                    if should_check_swapped:
                         # e.g. check if "Stenford" (was target_last) matches given "Stenford"
                         # and "Ruvinga" (was target_first) matches family "Ruvinga"
                         if names_match(target_last, target_first, given, family):
                              match_found = True
                              break
                
                if match_found:
                    filtered_works.append(work)
                else:
                    logging.debug(f"Filtered out result '{work.title}' - no match for author {author}")
            
            
                
            # Filter matches
            works = filtered_works
            
            # Apply year/type filters if provided
            if kwargs:
                works = self._filter_results(works, **kwargs)

            # Assign metadata
            for work in works:
                # Default metadata for author search
                if not hasattr(work, 'match_type'):
                    work.match_type = 'author_match'
                if not hasattr(work, 'confidence_score'):
                    work.confidence_score = 1.0 # Assumed high if returned by API and filtered
                if not hasattr(work, 'retrieval_method'):
                    work.retrieval_method = 'api'
                if not hasattr(work, 'source'):
                    work.source = 'aggregated'
                
                # Author ambiguity hook
                if not hasattr(work, 'author_ambiguity'):
                    # Check for potential ambiguity (e.g. single name, "et al", or many authors)
                    authors = work.authors if isinstance(work.authors, list) else str(work.authors or "").split(', ')
                    work.author_ambiguity = 0.0
                    if len(authors) == 1 and " " not in authors[0].strip():
                         work.author_ambiguity = 0.8 # Single token name often ambiguous
                    elif len(authors) > 50:
                         work.author_ambiguity = 0.2 # Massive collaboration

            # Deduplicate before invariant check and caching
            if works:
                works = self._deduplicate_results(works)

            if works:
                # Apply invariants
                self._ensure_invariants(works)
                
                import copy
                import time
                self.cache[key] = {
                    'timestamp': time.time(),
                    'data': copy.deepcopy(works)
                }
                self._save_cache()
            # Return fresh copy to ensure isolation
            return copy.deepcopy(works)
        except Exception as e:
            logging.error(f"Error searching for author works: {e}")
            return []

    def export_bibtex(self, project_id: str = "default") -> str:
        """
        Export project references to BibTeX format.
        
        Args:
            project_id: Project to export from (default: "default")
        
        Returns:
            BibTeX string with all references
        
        Raises:
            ProjectNotFoundError: If project doesn't exist
        """
        # Performance optimization: use shallow copy (read-only operation)
        project = self._project_manager.get_or_create_project(project_id)
        refs = project.get_references(deep=False)
        return "\n\n".join([ref.to_bibtex() for ref in refs])

    def export_ris(self, project_id: str = "default") -> str:
        """
        Export project references to RIS format.
        
        Args:
            project_id: Project to export from (default: "default")
        
        Returns:
            RIS string with all references
        
        Raises:
            ProjectNotFoundError: If project doesn't exist
        """
        # Performance optimization: use shallow copy (read-only operation)
        project = self._project_manager.get_or_create_project(project_id)
        refs = project.get_references(deep=False)
        return "\n\n".join([ref.to_ris() for ref in refs])
    
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
    
    def _deduplicate_results(self, results: List[Publication]) -> List[Publication]:
        """Remove duplicate publications based on DOI and title similarity, merging metadata."""
        seen_dois = {} # Map DOI -> existing_pub
        seen_titles = {} # Map normalized_title -> existing_pub
        unique_results = []
        
        for pub in results:
            # 1. Check DOI (most reliable)
            existing_match = None
            
            if pub.doi:
                doi_normalized = pub.doi.lower().strip()
                if doi_normalized in seen_dois:
                    logging.debug(f"Merge candidate (DOI): {doi_normalized}")
                    existing_match = seen_dois[doi_normalized]
            
            # 2. Check title similarity if no DOI match found
            if not existing_match:
                title_normalized = pub.title.lower().strip()
                for seen_title, seen_pub in seen_titles.items():
                    similarity = fuzz.ratio(title_normalized, seen_title)
                    if similarity > 90:  # 90% similar = duplicate
                        logging.debug(f"Merge candidate (Title): {pub.title[:30]}... matches {seen_pub.title[:30]}...")
                        existing_match = seen_pub
                        break
            
            if existing_match:
                # Merge metadata from 'pub' into 'existing_match' if missing
                self._merge_metadata(existing_match, pub)
            else:
                # Add new unique result
                unique_results.append(pub)
                
                # Update lookups
                if pub.doi:
                    seen_dois[pub.doi.lower().strip()] = pub
                seen_titles[pub.title.lower().strip()] = pub
        
        return unique_results

    def _merge_metadata(self, target: Publication, source: Publication):
        """Merge metadata from source into target if missing in target."""
        # Merge key fields if target is empty/generic but source has data
        if not target.url and source.url:
            target.url = source.url
        if not target.isbn and source.isbn:
            target.isbn = source.isbn
        if not target.publisher and source.publisher:
            target.publisher = source.publisher
        if not target.doi and source.doi:
            target.doi = source.doi
        # Also prefer year if target is "n.d."
        if (not target.year or target.year == "n.d.") and source.year and source.year != "n.d.":
            target.year = source.year
    
    def _rank_results(self, results: List[Tuple[Publication, str]], query: str, search_mode: str = 'general') -> List[Publication]:
        """Rank results and return sorted list."""
        if not results:
            return []
        
        # Source weights
        source_weights = {
            'crossref': 10,
            'pubmed': 9,
            'google_books': 7,
            'semantic_scholar': 8,
            'arxiv': 8
        }
        
        scored_results = []
        query_lower = query.lower()
        
        # Max possible score calculation (approximate)
        # Source(10) + TitleExact(100) + Recent(5) + DOI(3) + Authors(2) + Journal(1) = 121
        MAX_SCORE = 121.0
        
        # Stopwords to filter out (common words that don't indicate relevance)
        STOPWORDS = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'should', 'could', 'may', 'might', 'must', 'can', 'let',
            'get', 'got', 'make', 'made', 'take', 'took', 'give', 'gave', 'how',
            'what', 'when', 'where', 'who', 'why', 'which', 'this', 'that', 'these',
            'those', 'me', 'you', 'he', 'she', 'it', 'we', 'they', 'them', 'their'
        }
        
        # Pre-calculate query keywords for noise filtering (exclude stopwords)
        query_words = {
            w for w in re.findall(r'\w+', query_lower)
            if len(w) > 2 and w not in STOPWORDS
        }

        for pub, source in results:
            score = 0
            match_type = "fuzzy"
            criteria = {}
            
            # 1. Source reliability
            source_score = source_weights.get(source, 5)
            score += source_score
            criteria['source'] = source_score
            
            # 2. Query match in title
            title_lower = pub.title.lower() if pub.title else ""
            
            # Phrase-aware matching: Detect educational qualification terms
            # These should be treated as compound phrases, not generic "level" usage
            EDUCATIONAL_PHRASES = [
                r'\ba[-\' ]?level\b',      # A-level, A level, A'level
                r'\bo[-\' ]?level\b',      # O-level, O level, O'level
                r'\bas[-\' ]?level\b',     # AS-level, AS level
                r'\bcollege[-\' ]?level\b', # college-level
                r'\bhigher level\b',       # higher level (IB)
                r'\bstandard level\b',     # standard level (IB)
                r'\bgraduate[-\' ]?level\b', # graduate-level
                r'\bundergraduate[-\' ]?level\b' # undergraduate-level
            ]
            
            # Check if query contains educational phrases
            query_has_edu_phrase = any(re.search(pattern, query_lower) for pattern in EDUCATIONAL_PHRASES)
            title_has_edu_phrase = any(re.search(pattern, title_lower) for pattern in EDUCATIONAL_PHRASES)
            
            if title_lower == query_lower:
                score += 100
                match_type = "exact_title"
                criteria['title_exact'] = 100
            elif query_lower in title_lower:
                score += 50
                match_type = "partial_title"
                criteria['title_partial'] = 50
            # Boost if both query and title contain educational phrases
            elif query_has_edu_phrase and title_has_edu_phrase:
                score += 40
                match_type = "educational_phrase_match"
                criteria['educational_phrase'] = 40
            else:
                # Fuzzy/Keyword matching
                ratio = fuzz.partial_ratio(query_lower, title_lower)
                if ratio >= 90:
                    score += 45
                    match_type = "fuzzy_title_high"
                    criteria['title_fuzzy_high'] = 45
                elif ratio >= 70:
                    score += 25
                    match_type = "fuzzy_title_mid"
                    criteria['title_fuzzy_mid'] = 25
                
                # Title keyword overlap (require meaningful overlap)
                title_words = set(re.findall(r'\w+', title_lower))
                overlap = query_words.intersection(title_words)
                
                # Only award points for sufficient keyword overlap
                if len(overlap) >= 2:
                    # Multiple keywords match
                    overlap_score = len(overlap) * 10
                    
                    # Proximity bonus: Keywords appearing close together (within 3 words)
                    # This helps distinguish "A-level mathematics" from "multi-level deep learning models"
                    title_words_list = re.findall(r'\w+', title_lower)
                    keyword_positions = {}
                    for keyword in overlap:
                        positions = [i for i, w in enumerate(title_words_list) if w == keyword]
                        if positions:
                            keyword_positions[keyword] = positions[0]  # Use first occurrence
                    
                    # Check if keywords are within proximity window (3 words)
                    if len(keyword_positions) >= 2:
                        positions = sorted(keyword_positions.values())
                        min_distance = min(positions[i+1] - positions[i] for i in range(len(positions)-1))
                        
                        if min_distance <= 3:
                            # Keywords are close together - strong relevance signal
                            proximity_bonus = 15
                            score += proximity_bonus
                            criteria['keyword_proximity'] = proximity_bonus
                    
                    score += overlap_score
                    criteria['title_keywords'] = overlap_score
                    if match_type == "fuzzy":
                        match_type = "keyword_match"
                elif len(overlap) == 1 and len(query_words) == 1:
                    # Single keyword match, but only if query is single keyword
                    overlap_score = 10
                    score += overlap_score
                    criteria['title_keywords'] = overlap_score
                    if match_type == "fuzzy":
                        match_type = "keyword_match"
            
            # Phrase Mismatch Penalty
            # If query has educational phrase (e.g., "A-level") but title doesn't, apply penalty
            if query_has_edu_phrase and not title_has_edu_phrase:
                score -= 30
                criteria['edu_phrase_mismatch'] = -30
            
            # 3. Recency (2020+ gets bonus)
            try:
                year = int(pub.year) if pub.year and str(pub.year).isdigit() else 0
                if year >= 2020:
                    score += 5
                    criteria['year_2020_plus'] = 5
                elif year >= 2015:
                    score += 2
                    criteria['year_2015_plus'] = 2
            except:
                pass
            
            # 4. Completeness
            if pub.doi:
                score += 3
                criteria['has_doi'] = 3
            if pub.authors:
                score += 2
                criteria['has_authors'] = 2
            if pub.journal or pub.publisher:
                score += 1
                criteria['has_venue'] = 1
                
            # Populate metadata
            pub.confidence_score = max(0.0, min(score / MAX_SCORE, 1.0))
            pub.match_type = match_type
            pub.retrieval_method = "api" 
            if not hasattr(pub, 'author_ambiguity'):
                 pub.author_ambiguity = 0.0
            
            scored_results.append((score, pub, source, criteria))
        
        # Deterministic sorting key
        def sort_key(item):
            score, pub, _, _ = item
            
            # 1. Primary: Score (Descending)
            k_score = -score
            
            # 2. Secondary: Normalized Title (Ascending)
            k_title = (pub.title or "").strip().lower()
            
            # 3. Tertiary: DOI (Ascending)
            k_doi = (pub.doi or "").strip().lower()
            
            # 4. Quaternary: Year (Descending, None last)
            # Map valid years to negative integers so older years are "larger" (come later)
            # Map invalid/missing years to positive integer (come last)
            k_year = 1  # Default for missing/invalid ("last")
            if pub.year:
                try:
                    # Extract first 4-digit sequence
                    match = re.search(r'\d{4}', str(pub.year))
                    if match:
                        k_year = -int(match.group(0))
                except (ValueError, TypeError):
                    pass
            
            return (k_score, k_title, k_doi, k_year)

        # Sort by score (highest first) with deterministic tie-breaking
        scored_results.sort(key=sort_key)
        
        best_pubs = []
        for i, (score, pub, source, criteria) in enumerate(scored_results):
            if i == 0:
                pub.is_selected = True
                pub.selection_details = {
                    'score': score,
                    'criteria': criteria
                }
            else:
                pub.is_selected = False
            
            # Filter out "stray" results (low score and insufficient keyword match)
            
            # Calculate keyword overlap for noise filtering
            pub_title_lower = pub.title.lower() if pub.title else ""
            title_tokens = set(re.findall(r'\w+', pub_title_lower))
            overlap = query_words.intersection(title_tokens)
            overlap_count = len(overlap)
            
            # Check for educational phrase mismatch
            # If query has educational phrase (e.g., "A-level") but title doesn't, likely irrelevant
            EDUCATIONAL_PHRASES = [
                r'\ba[-\' ]?level\b', r'\bo[-\' ]?level\b', r'\bas[-\' ]?level\b',
                r'\bcollege[-\' ]?level\b', r'\bhigher level\b', r'\bstandard level\b',
                r'\bgraduate[-\' ]?level\b', r'\bundergraduate[-\' ]?level\b'
            ]
            query_has_edu_phrase = any(re.search(pattern, query_lower) for pattern in EDUCATIONAL_PHRASES)
            title_has_edu_phrase = any(re.search(pattern, pub_title_lower) for pattern in EDUCATIONAL_PHRASES)
            
            # Noise filtering strategy:
            # Drop results with low scores AND insufficient keyword overlap
            should_drop = False
            
            # 1. Educational phrase mismatch: Query has edu phrase but title doesn't
            if query_has_edu_phrase and not title_has_edu_phrase:
                # Allow high-scoring exact matches to pass through
                if score < 60:
                    should_drop = True
            
            # 2. Hard Drop: Low score AND insufficient keyword overlap
            elif score < 20 and overlap_count < 2:
                should_drop = True
            
            # 3. Contextual Drop: If best result is strong (>90), be stricter
            elif scored_results[0][0] > 90 and score < 30:
                should_drop = True
            
            # 4. Zero overlap: Always drop if no meaningful keywords match
            elif overlap_count == 0 and len(query_words) > 0:
                should_drop = True

            # 5. Strict Title Mode: Drop if title match < 80 and not exact
            if search_mode == 'title' and not should_drop:
                # Require reasonably high match for "title search" mode
                if "title_partial" in criteria or "title_exact" in criteria:
                    pass # Keep it
                elif "educational_phrase_match" in criteria:
                    pass # Keep it
                elif "fuzzy_title_high" in criteria:
                    pass # Keep it (>90)
                elif "fuzzy_title_mid" in criteria: 
                    # Drop mid-range matches in strict title mode if there are no other strong signals
                    # Relaxed threshold from 60 to 45 to allow legitimate matches with slight variations
                    if score < 45:
                        should_drop = True
                        logging.debug(f"Dropped strict title result (score={score}): {pub.title}")
                else:
                     # Drop low fuzzy matches or keyword-only matches in strict title mode
                     # BUT keep if we have strong keyword proximity signal
                     if "keyword_proximity" in criteria and score > 40:
                         pass
                     else:
                        should_drop = True
                        logging.debug(f"Dropped strict title result (no strong title match): {pub.title}")

            if not should_drop:
                best_pubs.append(pub)
            else:
                logging.debug(f"Dropped noise result (score={score}, overlap={overlap_count}, edu_mismatch={query_has_edu_phrase and not title_has_edu_phrase}): {pub.title[:30]}...")
        
        # Re-sort final list to ensure demotions (if any logic added for that) or just stable score sort
        # Currently the list is built in score order.
        # If we wanted to "demote", we would append to a "low_confidence" list and concat.
        # But simply keeping them with low scores puts them at the bottom naturally.
        # The key is we didn't drop them.
        
        if best_pubs:
            logging.debug(f"Top result (score={scored_results[0][0]}, conf={best_pubs[0].confidence_score:.2f}): {best_pubs[0].title[:50]}...")
            if hasattr(best_pubs[0], 'selection_details'):
                logging.debug(f"Selection details: {best_pubs[0].selection_details}")
        
        if best_pubs:
            logging.debug(f"Top result (score={scored_results[0][0]}, conf={best_pubs[0].confidence_score:.2f}): {best_pubs[0].title[:50]}...")
            if hasattr(best_pubs[0], 'selection_details'):
                logging.debug(f"Selection details: {best_pubs[0].selection_details}")
        
        return best_pubs
        
    def _filter_results(self, results: List[Publication], **kwargs) -> List[Publication]:
        """Apply fallback filters that must be true for all results."""
        filtered_results = []
        
        year_from = kwargs.get('year_from')
        year_to = kwargs.get('year_to')
        doc_type = kwargs.get('document_type')
        
        for pub in results:
            keep = True
            
            # Filter by Year
            if year_from or year_to:
                try:
                    # Robust year parsing
                    y_str = str(pub.year)
                    # Extract first 4 digits found
                    match = re.search(r'\d{4}', y_str)
                    if match:
                        y = int(match.group(0))
                        if year_from and y < year_from:
                            keep = False
                        if year_to and y > year_to:
                            keep = False
                    else:
                        # If we can't parse a year, we generally keep it unless strict?
                        # Fallback: treat as 0 or ignore. Let's act like app.py: 0
                        y = 0
                        # If year filtering is active and we have no valid year, 
                        # usually we might exclude it.
                        if year_from and y < year_from:
                            keep = False
                        if year_to and y > year_to:
                            keep = False
                except (ValueError, TypeError):
                    if year_from or year_to:
                        keep = False
            
            # Filter by Document Type
            if keep and doc_type:
                # Simple check against pub_type
                if pub.pub_type.lower() != doc_type.lower():
                    keep = False
            
            if keep:
                filtered_results.append(pub)
                
        return filtered_results
    
    def parallel_search(self, query: str, limit: int = 5, search_mode: str = 'general', **kwargs) -> List[Publication]:
        """Search all sources in parallel and return ranked list."""
        
        import time
        search_start = time.time()
        
        all_results = []
        
        # Extract filters
        year_from = kwargs.get('year_from')
        year_to = kwargs.get('year_to')
        doc_type = kwargs.get('document_type')
        language = kwargs.get('language')
        open_access = kwargs.get('open_access')
        
        # Execute all searches concurrently
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_source = {}
            
            # CrossRef: supports date range and type
            # Note: mapping 'document_type' (UI) -> 'doc_type' (API)
            cr_kwargs = {}
            if year_from: cr_kwargs['year_from'] = year_from
            if year_to: cr_kwargs['year_to'] = year_to
            if doc_type: cr_kwargs['doc_type'] = doc_type
            
            future_to_source[executor.submit(
                self.crossref.search, query, limit, search_mode=search_mode, **cr_kwargs
            )] = 'crossref'
        
            # PubMed: supports date range, language, open_access
            pm_kwargs = {}
            if year_from: pm_kwargs['year_from'] = year_from
            if year_to: pm_kwargs['year_to'] = year_to
            if language: pm_kwargs['language'] = language
            if open_access: pm_kwargs['open_access'] = open_access
            
            future_to_source[executor.submit(
                self.pubmed.search, query, limit, search_mode=search_mode, **pm_kwargs
            )] = 'pubmed'
            
            # Google Books: supports language
            gb_kwargs = {}
            if language: gb_kwargs['language'] = language
            
            future_to_source[executor.submit(
                self.google_books.search, query, limit, search_mode=search_mode, **gb_kwargs
            )] = 'google_books'
            
            # Collect results as they complete
            for future in as_completed(future_to_source):
                source = future_to_source[future]
                source_start = time.time()
                try:
                    results_list = future.result(timeout=10)
                    elapsed = time.time() - source_start
                    if results_list:
                        logging.info(f"Got {len(results_list)} results from {source} in {elapsed:.2f}s")
                        for res in results_list:
                            all_results.append((res, source))
                    else:
                        logging.info(f"{source} returned no results in {elapsed:.2f}s")
                except TimeoutError:
                    elapsed = time.time() - source_start
                    logging.warning(f"Timeout from {source} after {elapsed:.2f}s")
                except Exception as e:
                    elapsed = time.time() - source_start
                    logging.warning(f"Error from {source} after {elapsed:.2f}s: {e}")
        
        if not all_results:
            return []
            
        # Deduplicate
        unique_pubs = self._deduplicate_results([x[0] for x in all_results])
        
        # Re-associate with source (heuristic: find first match in all_results)
        # Or better: keep (pub, source) tuples through deduplication if possible?
        # _deduplicate_results currently returns List[Publication].
        # Let's just pass List[Publication] to rank_results, but rank_results expects List[Tuple[Publication, str]].
        # Wait, _rank_results calculates source score. I need the source.
        # My _deduplicate_results implementation discards source info (it takes List[Publication]).
        # I should update deduplication to handle tuples or re-attach.
        # For minimum impact refactor:
        # Re-attach source by looking up in all_results.
        
        unique_pubs_with_source = []
        for pub in unique_pubs:
            # finds the source for this pub
            src = 'unknown'
            for p, s in all_results:
                if p == pub:
                    src = s
                    break
            unique_pubs_with_source.append((pub, src))
            
        # Rank
        ranked = self._rank_results(unique_pubs_with_source, query, search_mode=search_mode)
        
        # Apply fallback filters (year, type)
        # This ensures that if a source ignores the filter (e.g. Google Books matching '1990' when asking for '2020'), we still respect user intent.
        final_results = self._filter_results(ranked, **kwargs)
        
        # Invariant check
        self._ensure_invariants(final_results)
        
        total_elapsed = time.time() - search_start
        logging.info(f"Parallel search completed in {total_elapsed:.2f}s, returned {len(final_results)} results")
        
        return final_results

    def _ensure_invariants(self, results: List[Publication]) -> None:
        """Enforce internal correctness guarantees (fail fast)."""
        if not isinstance(results, list):
             raise AssertionError("Retrieval invariant failed: results must be a list")
        
        seen_identifiers = set()
        for i, pub in enumerate(results):
             if not pub:
                  raise AssertionError(f"Retrieval invariant failed: null result at index {i}")
             if not pub.title:
                  raise AssertionError(f"Retrieval invariant failed: result {i} missing title")
             
             # Uniqueness check (if DOI present)
             if pub.doi:
                 # Normalize DOI for check
                 doi_norm = pub.doi.lower().strip()
                 if doi_norm in seen_identifiers:
                      raise AssertionError(f"Retrieval invariant failed: duplicate DOI detected {doi_norm}")
                 seen_identifiers.add(doi_norm)

    def enrich_publication(self, pub: Publication) -> Publication:
        """
        Attempt to enrich publicaton metadata (fix truncation).
        Fetches full details from CrossRef if possible.
        """
        try:
            logging.info(f"Enriching publication: {pub.title[:30]}...")
            
            # 1. Try DOI lookup if available
            if pub.doi:
                enriched = self.crossref.search_doi(pub.doi)
                if enriched:
                    logging.info("Enriched via DOI")
                    # Preserve match metadata if needed, but usually fresh data is better
                    return enriched
            
            # 2. Try strict title search (heuristic for truncation)
            # If we don't have a DOI, search CrossRef by title
            candidates = self.crossref.search(pub.title, rows=1)
            if candidates:
                candidate = candidates[0]
                # Fuzzy verification
                ratio = fuzz.ratio(pub.title.lower(), candidate.title.lower())
                partial = fuzz.partial_ratio(pub.title.lower(), candidate.title.lower())
                
                # If high match or original is clearly a substring of finding (truncation)
                if ratio > 80 or (partial > 90 and len(candidate.title) > len(pub.title)):
                    logging.info(f"Enriched via Title Search (score={ratio}, partial={partial})")
                    return candidate
            
            return pub
        except Exception as e:
            logging.error(f"Enrichment failed: {e}")
            return pub

