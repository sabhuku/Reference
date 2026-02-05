"""
Project Manager for multi-project reference storage.

This module provides the ProjectManager class which manages multiple
isolated projects with atomic persistence to a JSON file.

Design principles:
- Explicit project resolution (no hidden state)
- Only "default" project auto-created
- Deterministic JSON output (sorted keys)
- Atomic writes (temp file + rename)
"""
import json
import os
import shutil
import tempfile
from datetime import datetime
from typing import Dict, List, Optional

from .project import Project


class ProjectNotFoundError(Exception):
    """Raised when a non-existent project is requested."""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        super().__init__(f"Project '{project_id}' not found. Only 'default' is auto-created.")


class ProjectExistsError(Exception):
    """Raised when attempting to create a project that already exists."""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        super().__init__(f"Project '{project_id}' already exists.")


class ProjectManager:
    """
    Manages multiple projects with persistence.
    
    This class provides:
    - Project CRUD operations
    - Automatic "default" project creation
    - Atomic JSON persistence
    - Deterministic serialization
    
    Thread-safety note:
        This class does NOT provide thread-safety guarantees.
        Designed for request-scoped operations in Flask (multi-process).
        For multi-threaded access, caller must synchronize.
    
    Attributes:
        storage_path: Path to the JSON storage file
    """
    
    STORAGE_VERSION = "1.0"
    DEFAULT_PROJECT_ID = "default"
    DEFAULT_PROJECT_NAME = "Default Project"
    
    def __init__(self, storage_path: str = "projects.json"):
        """
        Initialize ProjectManager.
        
        Args:
            storage_path: Path to JSON file for persistence.
                         Relative paths are relative to current working directory.
        """
        self._projects: Dict[str, Project] = {}
        self._storage_path: str = storage_path
        self._loaded: bool = False
    
    @property
    def storage_path(self) -> str:
        """Return the storage path."""
        return self._storage_path
    
    def create_project(self, name: str, project_id: Optional[str] = None) -> Project:
        """
        Create a new project.
        
        Args:
            name: Human-readable project name
            project_id: Optional explicit ID. If None, generates UUID.
        
        Returns:
            Newly created Project instance
        
        Raises:
            ProjectExistsError: If project with same ID already exists
            ValueError: If name is empty
        """
        if not name or not isinstance(name, str):
            raise ValueError("name must be a non-empty string")
        
        if project_id is None:
            import uuid
            project_id = str(uuid.uuid4())
        
        if project_id in self._projects:
            raise ProjectExistsError(project_id)
        
        project = Project(project_id, name)
        self._projects[project_id] = project
        return project
    
    def get_project(self, project_id: str) -> Optional[Project]:
        """
        Get project by ID.
        
        Does NOT auto-create any projects.
        
        Args:
            project_id: Project identifier
        
        Returns:
            Project if found, None otherwise
        """
        return self._projects.get(project_id)
    
    def get_or_create_project(self, project_id: str) -> Project:
        """
        Get existing project or create if "default".
        
        IMPORTANT: Only the "default" project is auto-created.
        All other project_ids must already exist.
        
        Args:
            project_id: Project identifier
        
        Returns:
            Project instance
        
        Raises:
            ProjectNotFoundError: If non-default project doesn't exist
        """
        if project_id in self._projects:
            return self._projects[project_id]
        
        # Only auto-create the default project
        if project_id == self.DEFAULT_PROJECT_ID:
            return self.create_project(self.DEFAULT_PROJECT_NAME, project_id)
        
        raise ProjectNotFoundError(project_id)
    
    def list_projects(self) -> List[Project]:
        """
        List all projects in sorted order.
        
        DETERMINISM: Projects are returned sorted by ID for stable iteration.
        
        Returns:
            List of projects sorted by ID
        """
        return [self._projects[pid] for pid in sorted(self._projects.keys())]
    
    def delete_project(self, project_id: str) -> bool:
        """
        Delete a project.
        
        Args:
            project_id: Project to delete
        
        Returns:
            True if deleted, False if not found
        """
        if project_id in self._projects:
            del self._projects[project_id]
            return True
        return False
    
    def project_exists(self, project_id: str) -> bool:
        """Check if a project exists."""
        return project_id in self._projects
    
    def project_count(self) -> int:
        """Return number of managed projects."""
        return len(self._projects)
    
    def save(self) -> None:
        """
        Atomically save all projects to JSON file.
        
        GUARANTEES:
        - Atomic: Uses temp file + rename (POSIX rename is atomic)
        - Deterministic: Sorted keys for identical output
        - Corruption-resistant: Complete write or no change
        
        Raises:
            IOError: If write fails
        """
        # Build deterministic data structure
        data = {
            'version': self.STORAGE_VERSION,
            'saved_at': datetime.now().isoformat(),
            'projects': {}
        }
        
        # Serialize projects in sorted order for determinism
        for project_id in sorted(self._projects.keys()):
            project = self._projects[project_id]
            data['projects'][project_id] = project.to_dict()
        
        # Get directory for temp file (same directory as target)
        target_dir = os.path.dirname(os.path.abspath(self._storage_path)) or '.'
        
        # Atomic write: temp file + rename
        fd, temp_path = tempfile.mkstemp(
            suffix='.json.tmp',
            dir=target_dir
        )
        
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as tf:
                json.dump(
                    data,
                    tf,
                    indent=2,
                    ensure_ascii=False,
                    sort_keys=True  # Deterministic JSON key order
                )
                tf.flush()
                os.fsync(tf.fileno())  # Force write to disk
            
            # Atomic replace
            shutil.move(temp_path, self._storage_path)
            
        except Exception:
            # Cleanup temp file on error
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except OSError:
                pass
            raise
    
    def load(self) -> None:
        """
        Load all projects from JSON file.
        
        If file doesn't exist, starts with empty project set.
        Validates storage version for forward compatibility.
        
        Raises:
            ValueError: If storage version is unsupported
            json.JSONDecodeError: If file is malformed
        """
        if not os.path.exists(self._storage_path):
            self._projects = {}
            self._loaded = True
            return
        
        with open(self._storage_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Version check
        version = data.get('version', '0.0')
        if version != self.STORAGE_VERSION:
            raise ValueError(
                f"Unsupported storage version: {version}. "
                f"Expected: {self.STORAGE_VERSION}"
            )
        
        # Load projects
        self._projects = {}
        for project_id, project_data in data.get('projects', {}).items():
            self._projects[project_id] = Project.from_dict(project_data)
        
        self._loaded = True
    
    def is_loaded(self) -> bool:
        """Check if projects have been loaded from storage."""
        return self._loaded
    
    def ensure_loaded(self) -> None:
        """Load from storage if not already loaded."""
        if not self._loaded:
            self.load()
    
    def clear_all(self) -> None:
        """
        Remove all projects.
        
        USE WITH CAUTION: This removes all data in memory.
        Call save() to persist the change.
        """
        self._projects.clear()
    
    def to_dict(self) -> Dict:
        """
        Return full state as dictionary.
        
        Useful for debugging and testing.
        """
        return {
            'version': self.STORAGE_VERSION,
            'project_count': len(self._projects),
            'project_ids': sorted(self._projects.keys()),
            'loaded': self._loaded,
            'storage_path': self._storage_path
        }
    
    def __repr__(self) -> str:
        return (
            f"ProjectManager(projects={len(self._projects)}, "
            f"storage={self._storage_path!r})"
        )
