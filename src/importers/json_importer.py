"""JSON Importer for application export format."""
import json
from typing import List, Dict, Any
from ..models import Publication
from .base import ReferenceImporter

class JSONImporter(ReferenceImporter):
    """Parses JSON files exported by this application."""
    
    def parse(self, content: str) -> List[Publication]:
        try:
            data = json.loads(content)
            
            # handle wrapper object
            if isinstance(data, dict):
                # Check for common wrapper keys
                wrapper_keys = ['references', 'items', 'publications', 'bibliography', 'entries']
                found_list = False
                for key in wrapper_keys:
                    # check both case-sensitive and lower
                    val = data.get(key) or data.get(key.title()) or data.get(key.lower())
                    if isinstance(val, list):
                        data = val
                        found_list = True
                        break
                
                # If no list found, treat as single object
                if not found_list:
                    data = [data]
            
            if not isinstance(data, list):
                return []
            
            publications = []
            for item in data:
                if isinstance(item, dict):
                    pub = self._dict_to_pub(item)
                    if pub:
                        publications.append(pub)
            return publications
            
        except json.JSONDecodeError:
            return []
            
    def _dict_to_pub(self, item: Dict[str, Any]) -> Publication:
        """Convert dictionary to Publication model with robust key handling."""
        # Normalize keys to lowercase
        d = {k.lower(): v for k, v in item.items()}
        
        # Extract Authors (handle list or string)
        authors = []
        # Check 'authors', 'author', 'creators'
        raw_auth = d.get('authors') or d.get('author') or d.get('creators')
        if isinstance(raw_auth, list):
            authors = [str(a) for a in raw_auth]
        elif isinstance(raw_auth, str):
            authors = [raw_auth] 
            
        # Map publication type
        pub_type = d.get('pub_type') or d.get('reference_type') or d.get('type') or 'unknown'
        
        # Check date fields
        year = d.get('year') or d.get('date') or d.get('issued') or ''
        if isinstance(year, dict) and 'date-parts' in year: # CSL JSON
            try:
                year = str(year['date-parts'][0][0])
            except:
                year = ''

        return Publication(
            source=d.get('source', 'json-import'),
            pub_type=str(pub_type),
            authors=authors,
            year=str(year),
            title=d.get('title', ''),
            journal=d.get('journal') or d.get('publication') or d.get('container-title', ''),
            publisher=d.get('publisher', ''),
            location=d.get('location') or d.get('place', ''),
            volume=str(d.get('volume', '')),
            issue=str(d.get('issue', '')),
            pages=str(d.get('pages', '')),
            doi=d.get('doi', '')
        )
