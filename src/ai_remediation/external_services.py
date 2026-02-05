"""
External Metadata Service for AI Remediation

Provides authoritative verification for critical fields (Title, Author, Year, Publisher)
using CrossRef and Google Books APIs.
"""
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime

from src.referencing.utils.api_utils import safe_crossref_request, safe_google_books_request

logger = logging.getLogger(__name__)

class ExternalMetadataService:
    """
    Fetches and normalizes metadata from external authoritative sources.
    
    Priority:
    1. CrossRef (for Articles/DOIs)
    2. Google Books (for Books/ISBNs)
    """
    
    def fetch_metadata(self, reference: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Fetch verified metadata for a reference.
        
        Args:
            reference: Reference dictionary
            
        Returns:
            Dictionary matching 'external_metadata' schema or None
        """
        # 1. Try DOI lookup (Strongest signal)
        doi = reference.get('doi')
        if doi:
            logger.info(f"Fetching metadata via DOI: {doi}")
            metadata = self._fetch_crossref_by_doi(doi)
            if metadata:
                return metadata
        
        # 2. Try ISBN lookup (Strong signal for books)
        isbn = reference.get('isbn')
        if isbn:
            logger.info(f"Fetching metadata via ISBN: {isbn}")
            metadata = self._fetch_google_books_by_isbn(isbn)
            if metadata:
                return metadata
                
        # 3. Fallback: Search by title (Weaker signal, requires validation)
        title = reference.get('title')
        if title:
            # Decide source based on type
            ref_type = reference.get('type', 'book')
            
            if ref_type in ['journal', 'article-journal', 'journal-article']:
                logger.info(f"Searching CrossRef by title: {title}")
                return self._search_crossref(title)
            else:
                logger.info(f"Searching Google Books by title: {title}")
                return self._search_google_books(title)
                
        return None

    def _fetch_crossref_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """Fetch from CrossRef by DOI."""
        try:
            url = f"https://api.crossref.org/works/{doi}"
            data = safe_crossref_request(url)
            
            if data and data.get('message'):
                item = data['message']
                return self._normalize_crossref(item, confidence=1.0)
        except Exception as e:
            logger.warning(f"CrossRef DOI lookup failed: {e}")
        return None

    def _fetch_google_books_by_isbn(self, isbn: str) -> Optional[Dict[str, Any]]:
        """Fetch from Google Books by ISBN."""
        try:
            url = "https://www.googleapis.com/books/v1/volumes"
            params = {'q': f"isbn:{isbn}"}
            data = safe_google_books_request(url, params)
            
            if data and data.get('totalItems', 0) > 0:
                item = data['items'][0].get('volumeInfo', {})
                return self._normalize_google_books(item, confidence=1.0)
        except Exception as e:
            logger.warning(f"Google Books ISBN lookup failed: {e}")
        return None
        
    def _search_crossref(self, title: str) -> Optional[Dict[str, Any]]:
        """Search CrossRef by title."""
        try:
            url = "https://api.crossref.org/works"
            params = {'query.title': title, 'rows': 1}
            data = safe_crossref_request(url, params)
            
            if data and data.get('message', {}).get('items'):
                item = data['message']['items'][0]
                # Basic fuzzy match check could go here
                return self._normalize_crossref(item, confidence=0.85)
        except Exception as e:
            logger.warning(f"CrossRef search failed: {e}")
        return None

    def _search_google_books(self, title: str) -> Optional[Dict[str, Any]]:
        """Search Google Books by title."""
        try:
            url = "https://www.googleapis.com/books/v1/volumes"
            params = {'q': f"intitle:{title}", 'maxResults': 1}
            data = safe_google_books_request(url, params)
            
            if data and data.get('totalItems', 0) > 0:
                item = data['items'][0].get('volumeInfo', {})
                return self._normalize_google_books(item, confidence=0.85)
        except Exception as e:
            logger.warning(f"Google Books search failed: {e}")
        return None

    def _normalize_crossref(self, item: Dict, confidence: float) -> Dict[str, Any]:
        """Normalize CrossRef response to schema."""
        # Extract date
        issued = item.get('issued', {}).get('date-parts', [[None]])[0][0]
        
        # Extract authors
        authors = []
        for author in item.get('author', []):
            if 'family' in author and 'given' in author:
                authors.append(f"{author['family']}, {author['given']}")
            elif 'name' in author:
                authors.append(author['name'])
                
        return {
            'source': 'crossref',
            'confidence': confidence,
            'retrieved_at': datetime.utcnow().isoformat(),
            'data': {
                'title': item.get('title', [''])[0],
                'authors': authors,
                'year': issued if issued else None,
                'publisher': item.get('publisher'),
                'doi': item.get('DOI'),
                'journal': item.get('container-title', [''])[0],
                'volume': item.get('volume'),
                'issue': item.get('issue'),
                'pages': item.get('page')
            }
        }

    def _normalize_google_books(self, item: Dict, confidence: float) -> Dict[str, Any]:
        """Normalize Google Books response to schema."""
        # Extract date
        pub_date = item.get('publishedDate', '')
        year = int(pub_date[:4]) if pub_date and pub_date[:4].isdigit() else None
        
        return {
            'source': 'google_books',
            'confidence': confidence,
            'retrieved_at': datetime.utcnow().isoformat(),
            'data': {
                'title': item.get('title'),
                'authors': item.get('authors', []),
                'year': year,
                'publisher': item.get('publisher'),
                'location': None, # Google Books rarely provides location
                'isbn': item.get('industryIdentifiers', [{}])[0].get('identifier')
            }
        }
