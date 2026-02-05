"""
Project domain model for isolated reference storage.

This module provides the Project class which encapsulates a collection of
references with strict isolation guarantees. Each project maintains its own
reference list with no shared mutable state.

Design principles:
- No hidden state
- Defensive copying on get_references()
- Insertion order preserved
- Deterministic serialization
"""
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Dict, List, Optional
import copy

from .models import Publication


class Project:
    """
    Represents an isolated project with its own references.
    
    Thread-safety note:
        This class does NOT provide thread-safety guarantees.
        It is designed for request-scoped operations in a Flask environment
        where each request operates in isolation (multi-process deployment).
        If multi-threaded access is required, the caller must synchronize.
    
    Attributes:
        id: Unique identifier (immutable after creation)
        name: Human-readable project name
        created_at: Timestamp of project creation
        last_modified: Timestamp of last modification
    """
    
    __slots__ = ('id', 'name', '_references', 'created_at', 'last_modified')
    
    def __init__(self, project_id: str, name: str):
        """
        Initialize a new project.
        
        Args:
            project_id: Unique identifier for the project
            name: Human-readable name
        
        Raises:
            ValueError: If project_id or name is invalid
        """
        self._validate_project_id(project_id)
        
        if not name or not isinstance(name, str):
            raise ValueError("name must be a non-empty string")
        
        self.id: str = project_id
        self.name: str = name
        self._references: List[Publication] = []
        self.created_at: datetime = datetime.now()
        self.last_modified: datetime = datetime.now()
    
    @staticmethod
    def _validate_project_id(project_id: str) -> None:
        """
        Validate project ID for security and correctness.
        
        Protection against:
        - Path traversal attacks (../, ./)
        - SQL injection (later database migration)
        - Filesystem attacks (CON, PRN, NUL on Windows)
        - Denial of service (excessive length)
        
        Args:
            project_id: ID to validate
        
        Raises:
            ValueError: If project_id is invalid
        """
        import re
        
        if not project_id or not isinstance(project_id, str):
            raise ValueError("project_id must be a non-empty string")
        
        if len(project_id) > 255:
            raise ValueError("project_id too long (max 255 characters)")
        
        # Allow: alphanumeric, hyphens, underscores, dots
        # Reject: path separators, special chars, SQL injection patterns
        if not re.match(r'^[a-zA-Z0-9_\-\.]+$', project_id):
            raise ValueError(
                "project_id must contain only alphanumeric characters, "
                "hyphens, underscores, or dots"
            )
        
        # Reject path traversal patterns
        if '..' in project_id or project_id in {'.', '..'}:
            raise ValueError("project_id cannot contain path traversal patterns")
        
        # Reject Windows reserved names
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }
        if project_id.upper() in reserved_names:
            raise ValueError(f"'{project_id}' is a reserved system name")
    
    def add_reference(self, pub: Publication) -> None:
        """
        Add a reference to this project.
        
        Preserves insertion order for deterministic iteration.
        Updates last_modified timestamp.
        
        Args:
            pub: Publication to add
        
        Raises:
            TypeError: If pub is not a Publication instance
        """
        if not isinstance(pub, Publication):
            raise TypeError(f"Expected Publication, got {type(pub).__name__}")
        
        self._references.append(pub)
        self.last_modified = datetime.now()
    
    def remove_reference(self, pub: Publication) -> bool:
        """
        Remove a reference from this project.
        
        Uses identity comparison first, then equality.
        Updates last_modified timestamp if removed.
        
        Args:
            pub: Publication to remove
        
        Returns:
            True if removed, False if not found
        """
        # Try identity first
        for i, ref in enumerate(self._references):
            if ref is pub:
                del self._references[i]
                self.last_modified = datetime.now()
                return True
        
        # Try equality
        try:
            self._references.remove(pub)
            self.last_modified = datetime.now()
            return True
        except ValueError:
            return False
    
    def get_references(self, deep: bool = True) -> List[Publication]:
        """
        Return references from this project.
        
        ISOLATION GUARANTEE: By default, returns a deep copy to prevent
        external mutation from contaminating project state.
        
        Args:
            deep: If True (default), returns deep copy for full isolation.
                  If False, returns shallow copy (faster, but caller MUST NOT mutate).
        
        Returns:
            List of Publication objects
        
        Security Note:
            deep=False is provided for performance-critical code paths where
            the caller guarantees read-only access. Use with extreme caution.
        """
        if deep:
            return copy.deepcopy(self._references)
        return list(self._references)
    
    def get_references_shallow(self) -> List[Publication]:
        """
        Return shallow copy of references (performance optimization).
        
        DEPRECATED: Use get_references(deep=False) instead.
        
        WARNING: Caller MUST NOT mutate returned Publications.
        Mutation will contaminate project state.
        
        Returns:
            Shallow copy of references list
        """
        return list(self._references)
    
    def clear_references(self) -> None:
        """
        Remove all references from this project.
        
        Updates last_modified timestamp.
        """
        self._references.clear()
        self.last_modified = datetime.now()
    
    def reference_count(self) -> int:
        """Return number of references in this project."""
        return len(self._references)
    
    def to_dict(self) -> Dict:
        """
        Serialize project to dictionary for persistence.
        
        Produces deterministic output suitable for JSON serialization.
        Reference field order is preserved as per Publication dataclass definition.
        
        Returns:
            Dictionary representation of project
        """
        # Serialize references deterministically
        refs_serialized = []
        for pub in self._references:
            if is_dataclass(pub):
                pub_dict = asdict(pub)
            else:
                # Fallback for non-dataclass (shouldn't happen)
                pub_dict = {
                    'source': pub.source,
                    'pub_type': pub.pub_type,
                    'authors': pub.authors,
                    'year': pub.year,
                    'title': pub.title,
                    'journal': pub.journal,
                    'publisher': pub.publisher,
                    'location': pub.location,
                    'volume': pub.volume,
                    'issue': pub.issue,
                    'pages': pub.pages,
                    'doi': pub.doi,
                    'isbn': getattr(pub, 'isbn', ''),
                    'url': getattr(pub, 'url', ''),
                    'access_date': getattr(pub, 'access_date', ''),
                    'edition': getattr(pub, 'edition', ''),
                }
            refs_serialized.append(pub_dict)
        
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat(),
            'last_modified': self.last_modified.isoformat(),
            'references': refs_serialized
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Project':
        """
        Deserialize project from dictionary.
        
        Reconstructs Publication objects from serialized data.
        
        Args:
            data: Dictionary from to_dict() or JSON load
        
        Returns:
            Reconstructed Project instance
        
        Raises:
            KeyError: If required fields are missing
            ValueError: If data format is invalid
        """
        project = cls(data['id'], data['name'])
        
        # Parse timestamps
        project.created_at = datetime.fromisoformat(data['created_at'])
        project.last_modified = datetime.fromisoformat(data['last_modified'])
        
        # Reconstruct references
        for ref_data in data.get('references', []):
            # Extract Publication constructor args
            pub = Publication(
                source=ref_data.get('source', ''),
                pub_type=ref_data.get('pub_type', ''),
                authors=ref_data.get('authors', []),
                year=ref_data.get('year', ''),
                title=ref_data.get('title', ''),
                journal=ref_data.get('journal', ''),
                publisher=ref_data.get('publisher', ''),
                location=ref_data.get('location', ''),
                volume=ref_data.get('volume', ''),
                issue=ref_data.get('issue', ''),
                pages=ref_data.get('pages', ''),
                doi=ref_data.get('doi', ''),
                isbn=ref_data.get('isbn', ''),
                url=ref_data.get('url', ''),
                access_date=ref_data.get('access_date', ''),
                edition=ref_data.get('edition', ''),
                collection=ref_data.get('collection', ''),
                conference_name=ref_data.get('conference_name', ''),
                conference_location=ref_data.get('conference_location', ''),
                conference_date=ref_data.get('conference_date', ''),
                editor=ref_data.get('editor', ''),
            )
            
            # Restore additional metadata fields
            pub.match_type = ref_data.get('match_type', 'fuzzy')
            pub.confidence_score = ref_data.get('confidence_score', 0.0)
            pub.retrieval_method = ref_data.get('retrieval_method', 'loaded')
            pub.normalized_authors = ref_data.get('normalized_authors', [])
            pub.authors_inferred = ref_data.get('authors_inferred', False)
            pub.year_status = ref_data.get('year_status', 'present')
            pub.source_type_inferred = ref_data.get('source_type_inferred', False)
            pub.normalization_log = ref_data.get('normalization_log', [])
            
            project._references.append(pub)
        
        return project
    
    def __repr__(self) -> str:
        return f"Project(id={self.id!r}, name={self.name!r}, refs={len(self._references)})"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Project):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        return hash(self.id)
