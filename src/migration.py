"""
Migration utilities for project-scoped reference storage.

This module provides functions to migrate from the old global reference list
to the new project-scoped storage system.

Migration Strategy:
1. Existing session-based references (`refs` in Flask session) continue to work
2. For persistence, references can be migrated to ProjectManager storage
3. Backward compatibility is maintained via `self.refs` property on ReferenceManager
"""
import json
import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import asdict

from .models import Publication
from .project import Project
from .project_manager import ProjectManager


def migrate_session_refs_to_project(
    session_refs: List[Dict],
    project_manager: ProjectManager,
    project_id: str = "default"
) -> int:
    """
    Migrate session-based reference dicts to a project.
    
    This function takes the raw reference dicts from Flask session storage
    and adds them to the specified project.
    
    Args:
        session_refs: List of reference dicts from session['refs']
        project_manager: ProjectManager instance
        project_id: Target project ID (default: "default")
    
    Returns:
        Number of references migrated
    
    Example:
        >>> refs = session.get('refs', [])
        >>> migrated = migrate_session_refs_to_project(refs, project_manager)
        >>> print(f"Migrated {migrated} references")
    """
    project = project_manager.get_or_create_project(project_id)
    count = 0
    
    for ref_dict in session_refs:
        try:
            # Convert dict to Publication
            pub = dict_to_publication(ref_dict)
            project.add_reference(pub)
            count += 1
        except Exception as e:
            logging.warning(f"Failed to migrate reference: {e}")
    
    return count


def dict_to_publication(ref_dict: Dict) -> Publication:
    """
    Convert a reference dictionary to a Publication object.
    
    Handles missing fields gracefully by using defaults.
    
    Args:
        ref_dict: Reference dictionary (e.g., from session storage)
    
    Returns:
        Publication object
    """
    # Create Publication with all supported fields
    pub = Publication(
        source=ref_dict.get('source', 'migrated'),
        pub_type=ref_dict.get('pub_type', ''),
        authors=ref_dict.get('authors', []),
        year=ref_dict.get('year', ''),
        title=ref_dict.get('title', ''),
        journal=ref_dict.get('journal', ''),
        publisher=ref_dict.get('publisher', ''),
        location=ref_dict.get('location', ''),
        volume=ref_dict.get('volume', ''),
        issue=ref_dict.get('issue', ''),
        pages=ref_dict.get('pages', ''),
        doi=ref_dict.get('doi', ''),
        isbn=ref_dict.get('isbn', ''),
        url=ref_dict.get('url', ''),
        access_date=ref_dict.get('access_date', ''),
        edition=ref_dict.get('edition', ''),
        collection=ref_dict.get('collection', ''),
        conference_name=ref_dict.get('conference_name', ''),
        conference_location=ref_dict.get('conference_location', ''),
        conference_date=ref_dict.get('conference_date', ''),
        editor=ref_dict.get('editor', ''),
    )
    
    # Restore metadata fields if present
    pub.match_type = ref_dict.get('match_type', 'migrated')
    pub.confidence_score = ref_dict.get('confidence_score', 0.0)
    pub.retrieval_method = ref_dict.get('retrieval_method', 'migrated')
    pub.normalized_authors = ref_dict.get('normalized_authors', [])
    pub.authors_inferred = ref_dict.get('authors_inferred', False)
    pub.year_status = ref_dict.get('year_status', 'present')
    pub.source_type_inferred = ref_dict.get('source_type_inferred', False)
    pub.normalization_log = ref_dict.get('normalization_log', [])
    
    return pub


def migrate_old_cache_file(
    old_cache_path: str,
    project_manager: ProjectManager,
    project_id: str = "default"
) -> int:
    """
    Migrate references from an old cache file to a project.
    
    Handles the legacy cache.json format where references were stored
    in a 'references' key.
    
    Args:
        old_cache_path: Path to old cache.json file
        project_manager: ProjectManager instance
        project_id: Target project ID
    
    Returns:
        Number of references migrated, or 0 if file doesn't exist
    """
    if not os.path.exists(old_cache_path):
        return 0
    
    try:
        with open(old_cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Try different possible formats
        refs = []
        if 'references' in data:
            refs = data['references']
        elif isinstance(data, list):
            refs = data
        
        return migrate_session_refs_to_project(refs, project_manager, project_id)
    except Exception as e:
        logging.error(f"Failed to migrate from {old_cache_path}: {e}")
        return 0


def export_project_to_session_format(
    project_manager: ProjectManager,
    project_id: str = "default"
) -> List[Dict]:
    """
    Export project references back to session-compatible format.
    
    Useful for backward compatibility with code that expects
    List[Dict] format.
    
    Args:
        project_manager: ProjectManager instance
        project_id: Project to export
    
    Returns:
        List of reference dicts suitable for session['refs']
    """
    project = project_manager.get_or_create_project(project_id)
    refs = project.get_references()
    
    return [asdict(pub) if hasattr(pub, '__dataclass_fields__') else vars(pub)
            for pub in refs]


def verify_migration_integrity(
    original_refs: List[Dict],
    project_manager: ProjectManager,
    project_id: str = "default"
) -> Dict[str, Any]:
    """
    Verify that migration preserved all reference data.
    
    Compares original reference list against migrated project contents.
    
    Args:
        original_refs: Original reference dicts before migration
        project_manager: ProjectManager with migrated data
        project_id: Project to verify
    
    Returns:
        Dict with verification results:
        {
            'success': bool,
            'original_count': int,
            'migrated_count': int,
            'missing_titles': List[str],
            'extra_titles': List[str]
        }
    """
    project = project_manager.get_or_create_project(project_id)
    migrated_refs = project.get_references()
    
    original_titles = set(r.get('title', '') for r in original_refs)
    migrated_titles = set(p.title for p in migrated_refs)
    
    missing = original_titles - migrated_titles
    extra = migrated_titles - original_titles
    
    return {
        'success': len(missing) == 0 and len(original_refs) == len(migrated_refs),
        'original_count': len(original_refs),
        'migrated_count': len(migrated_refs),
        'missing_titles': list(missing),
        'extra_titles': list(extra)
    }


# CLI entry point for standalone migration
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate references to project storage")
    parser.add_argument("--source", required=True, help="Source JSON file with references")
    parser.add_argument("--output", default="projects.json", help="Output projects.json path")
    parser.add_argument("--project-id", default="default", help="Target project ID")
    
    args = parser.parse_args()
    
    pm = ProjectManager(storage_path=args.output)
    count = migrate_old_cache_file(args.source, pm, args.project_id)
    pm.save()
    
    print(f"Migrated {count} references to project '{args.project_id}'")
    print(f"Saved to {args.output}")
