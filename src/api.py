"""API client classes for external services."""
import logging
from typing import List, Optional, Dict
import requests

from .models import Publication
from .utils.error_handling import api_error_handler

class BaseAPI:
    """Base class for API clients."""
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    def _make_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """Make an HTTP request with error handling."""
        try:
            response = requests.get(
                f"{self.base_url}/{endpoint}",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"API request failed: {e}")
            return None

class CrossRefAPI(BaseAPI):
    """CrossRef API client."""
    def __init__(self, mailto: str):
        super().__init__("https://api.crossref.org/works")
        self.mailto = mailto
    
    @api_error_handler
    def search_single(self, query: str, rows: int = 1) -> Optional[Publication]:
        """Search for a single publication."""
        params = {
            "query.bibliographic": query,
            "rows": rows,
            "mailto": self.mailto
        }
        data = self._make_request("", params)
        if not data:
            return None
            
        items = data.get("message", {}).get("items", [])
        if not items:
            return None
            
        return self._parse_response(items[0])
    
    @api_error_handler
    def search_author(self, author: str, rows: int = 20) -> List[Publication]:
        """Search for works by an author with advanced name matching."""
        from .name_utils import names_match, guess_first_last_from_author_query
        
        target_first, target_last = guess_first_last_from_author_query(author)
        
        params = {
            "query.author": author,
            "rows": rows,
            "mailto": self.mailto
        }
        data = self._make_request("", params)
        if not data:
            return []
            
        items = data.get("message", {}).get("items", [])
        
        def filter_items(items, t_first, t_last):
            matches = []
            for item in items:
                # Check for match in any author of the work
                for a in item.get("author", []):
                    given = a.get("given", "")
                    family = a.get("family", "")
                    if names_match(t_first, t_last, given, family):
                        matches.append(item)
                        break
            return matches

        filtered_items = filter_items(items, target_first, target_last)
        
        # If no results and query is likely "FirstName LastName" (2 parts), try reversed "LastName FirstName"
        if not filtered_items and len(author.split()) == 2:
            # Swap interpretation: what was first is now last, and vice versa
            # Note: guess_first_last logic might have already split them.
            # Simplified swap:
            parts = author.split()
            # If original was A B, new try is B A
            # Recalculate targets manually or just swap what we got if simple
            if target_first and target_last and " " not in target_first and " " not in target_last:
                 # Try swapping
                 filtered_items = filter_items(items, target_last, target_first)

        return [self._parse_response(item) for item in filtered_items]

    @api_error_handler
    def search_doi(self, doi: str) -> Optional[Publication]:
        """Look up work by DOI."""
        # Clean DOI (remove dx.doi.org, https, etc)
        doi = doi.strip().replace("https://doi.org/", "").replace("http://dx.doi.org/", "")
        
        # Use direct work lookup endpoint
        url = f"https://api.crossref.org/works/{doi}"
        params = {"mailto": self.mailto}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
            item = data.get("message", {})
            return self._parse_response(item)
        except Exception as e:
            logging.error(f"DOI lookup failed: {e}")
            return None
    
    def _parse_response(self, item: Dict) -> Publication:
        """Parse CrossRef API response into Publication object."""
        return Publication(
            source="crossref",
            pub_type=item.get("type", "").lower(),
            authors=self._parse_authors(item),
            year=self._extract_year(item),
            title=item.get("title", ["NO TITLE"])[0],
            journal=(item.get("container-title") or [""])[0],
            publisher=item.get("publisher", ""),
            location="",
            volume=item.get("volume", ""),
            issue=item.get("issue", ""),
            pages=item.get("page", ""),
            doi=item.get("DOI", "")
        )
    
    @staticmethod
    def _parse_authors(item: Dict) -> List[str]:
        """Parse author information from CrossRef response."""
        authors = []
        for a in item.get("author", []):
            given = a.get("given", "")
            family = a.get("family", "")
            authors.append(f"{family}, {given}".strip(", "))
        return authors
    
    @staticmethod
    def _extract_year(item: Dict) -> str:
        """Extract publication year from CrossRef response."""
        for key in ["published-print", "published-online", "issued"]:
            if key in item and "date-parts" in item[key]:
                parts = item[key]["date-parts"]
                if parts and len(parts[0]) > 0:
                    return str(parts[0][0])
        return "n.d."

class GoogleBooksAPI(BaseAPI):
    """Google Books API client."""
    def __init__(self, api_key: str):
        super().__init__("https://www.googleapis.com/books/v1/volumes")
        self.api_key = api_key
    
    @api_error_handler
    def search_single(self, query: str, max_results: int = 5) -> Optional[Publication]:
        """Search for a single book."""
        params = {
            "q": query,
            "maxResults": max_results
        }
        if self.api_key:
            params["key"] = self.api_key
            
        data = self._make_request("", params)
        if not data:
            return None
            
        items = data.get("items", [])
        if not items:
            return None
            
        return self._parse_response(items[0])

    @api_error_handler
    def search_author(self, author: str, max_results: int = 10) -> List[Publication]:
        """Search for works by an author."""
        params = {
            "q": f"inauthor:{author}",
            "maxResults": max_results
        }
        if self.api_key:
            params["key"] = self.api_key
            
        data = self._make_request("", params)
        if not data:
            return []
            
        items = data.get("items", [])
        return [self._parse_response(item) for item in items if item]

    def _parse_response(self, item: Dict) -> Publication:
        """Parse Google Books API response into Publication object."""
        v = item.get("volumeInfo", {})
        
        # Handle authors
        raw_authors = v.get("authors", [])
        authors = []
        for a in raw_authors:
            # Simple author name cleaning
            authors.append(a)
            
        pubdate = v.get("publishedDate", "n.d.")
        year = pubdate.split("-")[0] if pubdate != "n.d." else "n.d."
        
        return Publication(
            source="google_books",
            pub_type="book",
            authors=authors,
            year=year,
            title=v.get("title", "NO TITLE"),
            journal="",
            publisher=v.get("publisher", ""),
            location="",
            volume="",
            issue="",
            pages=str(v.get("pageCount", "")),
            doi=""
        )