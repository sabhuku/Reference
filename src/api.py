"""API client classes for external services."""
import logging
import time
from typing import List, Optional, Dict
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .models import Publication
from .utils.error_handling import api_error_handler

class BaseAPI:
    """Base class for API clients with robust retry logic."""
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = self._create_retry_session()
    
    def _create_retry_session(self, retries=3, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504)):
        """Create a requests Session with retry logic."""
        session = requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            allowed_methods=frozenset(['GET', 'POST'])
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def _make_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """Make an HTTP request with error handling and retries."""
        try:
            url = f"{self.base_url}/{endpoint}" if endpoint else self.base_url
            response = self.session.get(
                url,
                params=params,
                timeout=15  # Increased timeout slightly for safety
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            # Check if it was a max retry error 
            logging.error(f"API request failed after retries: {e}")
            return None

class CrossRefAPI(BaseAPI):
    """CrossRef API client."""
    def __init__(self, mailto: str):
        super().__init__("https://api.crossref.org/works")
        self.mailto = mailto
        # Add User-Agent to be polite
        self.session.headers.update({
            'User-Agent': f'ReferenceManager/1.0 (mailto:{mailto})'
        })
    
    @api_error_handler
    def search_single(self, query: str, rows: int = 1) -> Optional[Publication]:
        """Search for a single publication."""
        results = self.search(query, rows)
        return results[0] if results else None
    
    @api_error_handler
    def search(self, query: str, rows: int = 5, year_from: Optional[int] = None, 
               year_to: Optional[int] = None, doc_type: Optional[str] = None,
               search_mode: str = 'general') -> List[Publication]:
        """Search for publications with optional filters."""
        params = {
            "rows": rows,
            "mailto": self.mailto
        }
        
        # Handle search mode
        if search_mode == 'title':
            params["query.title"] = query
        else:
            params["query.bibliographic"] = query
        
        # Build filter string
        filters = []
        if year_from:
            filters.append(f"from-pub-date:{year_from}")
        if year_to:
            filters.append(f"until-pub-date:{year_to}")
            
        if doc_type:
            # Map UI types to CrossRef types
            type_map = {
                'article': 'journal-article',
                'book': 'book',
                'conference': 'proceedings-article',
                'thesis': 'dissertation',
                'report': 'report'
            }
            cr_type = type_map.get(doc_type.lower())
            if cr_type:
                filters.append(f"type:{cr_type}")
        
        if filters:
            params["filter"] = ",".join(filters)
            
        data = self._make_request("", params)
        if not data:
            return []
            
        items = data.get("message", {}).get("items", [])
        return [self._parse_response(item) for item in items if item]
    
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
        
        filtered_items = []
        
        # Check if we should try reversed interpretation (if 2 words)
        try_reversed = False
        target_first_rev, target_last_rev = "", ""
        parts = author.split()
        if len(parts) == 2:
             try_reversed = True
             # Simple swap of the original guess or the raw parts
             target_first_rev = target_last
             target_last_rev = target_first

        for item in items:
            match_found = False
            # Check for match in any author of the work using primary guess
            for a in item.get("author", []):
                given = a.get("given", "")
                family = a.get("family", "")
                if names_match(target_first, target_last, given, family):
                    match_found = True
                    break
            
            # If no match and reversed is plausible, try that
            if not match_found and try_reversed:
                 for a in item.get("author", []):
                    given = a.get("given", "")
                    family = a.get("family", "")
                    if names_match(target_first_rev, target_last_rev, given, family):
                        match_found = True
                        break
            
            if match_found:
                filtered_items.append(item)

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
            doi=item.get("DOI", ""),
            isbn=item.get("ISBN", [""])[0] if item.get("ISBN") else ""
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
        results = self.search(query, max_results)
        return results[0] if results else None

    @api_error_handler
    def search(self, query: str, max_results: int = 5, language: Optional[str] = None,
               search_mode: str = 'general') -> List[Publication]:
        """Search for books with optional filters."""
        # Handle search mode
        q_param = f"intitle:{query}" if search_mode == 'title' else query
        
        params = {
            "q": q_param,
            "maxResults": max_results
        }
        
        if language:
            params["langRestrict"] = language
            
        if self.api_key:
            params["key"] = self.api_key
            
        data = self._make_request("", params)
        if not data:
            return []
            
        items = data.get("items", [])
        return [self._parse_response(item) for item in items if item]

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
        
        # Extract ISBN
        isbn = ""
        identifiers = v.get("industryIdentifiers", [])
        for ident in identifiers:
            if ident.get("type") == "ISBN_13":
                isbn = ident.get("identifier")
                break
            elif ident.get("type") == "ISBN_10" and not isbn:
                isbn = ident.get("identifier")
                
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
            doi="",
            isbn=isbn,
            url=v.get("infoLink", "")  # Add direct link to Google Books
        )


class PubMedAPI(BaseAPI):
    """PubMed E-utilities API client for biomedical literature."""
    
    def __init__(self):
        # We don't set a single base_url because PubMed uses different endpoints
        self.esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        self.esummary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        
        # Init session via specialized BaseAPI method
        self.session = self._create_retry_session()
        
        self.last_request_time = 0
        import threading
        self._lock = threading.Lock()
    
    def _rate_limit(self):
        """Enforce NCBI rate limit of 3 requests/second."""
        with self._lock:
            elapsed = time.time() - self.last_request_time
            if elapsed < 0.34:  # 0.34s = ~3 requests/second
                time.sleep(0.34 - elapsed)
            self.last_request_time = time.time()

    def _make_request(self, url: str, params: Dict) -> Optional[Dict]:
        """Override to use specific URL and self.session."""
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=15
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"PubMed API request failed: {e}")
            return None
    
    @api_error_handler
    def search_single(self, query: str) -> Optional[Publication]:
        """Search PubMed for a single article."""
        results = self.search(query, max_results=1)
        return results[0] if results else None

    @api_error_handler
    def search(self, query: str, max_results: int = 5, year_from: Optional[int] = None, 
               year_to: Optional[int] = None, language: Optional[str] = None, 
               open_access: bool = False, search_mode: str = 'general') -> List[Publication]:
        """Search PubMed for articles with optional filters."""
        # Step 1: Search for articles
        self._rate_limit()
        
        # Build search term with filters
        search_term = f"{query}[Title]" if search_mode == 'title' else query
        
        if language:
            lang_map = {
                'en': 'english',
                'fr': 'french',
                'de': 'german',
                'es': 'spanish',
                'zh': 'chinese'
            }
            lang_name = lang_map.get(language.lower(), language)
            search_term += f" AND {lang_name}[lang]"
            
        if open_access:
            search_term += " AND free full text[filter]"
            
        search_params = {
            'db': 'pubmed',
            'term': search_term,
            'retmax': max_results,
            'retmode': 'json'
        }
        
        if year_from:
            search_params['mindate'] = str(year_from)
        if year_to:
            search_params['maxdate'] = str(year_to)
        
        search_data = self._make_request(self.esearch_url, search_params)
        
        # Extract PMID from results
        id_list = search_data.get('esearchresult', {}).get('idlist', []) if search_data else []
        if not id_list:
            if search_data: # Only log if we actually got a response but no IDs
                 logging.info(f"No PubMed results for: {query}")
            return []
        
        # Step 2: Get article metadata
        self._rate_limit()
        summary_params = {
            'db': 'pubmed',
            'id': ",".join(id_list),
            'retmode': 'json'
        }
        
        summary_data = self._make_request(self.esummary_url, summary_params)
        if not summary_data:
            return []
        
        results = []
        for pmid in id_list:
            # Extract article metadata
            article = summary_data.get('result', {}).get(str(pmid), {})
            if article:
                    pub = self._parse_response(article, pmid)
                    if pub:
                        results.append(pub)
        return results
    
    @api_error_handler
    def search_author(self, author: str, max_results: int = 10) -> List[Publication]:
        """Search PubMed for works by an author."""
        # Step 1: Search for articles by author
        self._rate_limit()
        search_params = {
            'db': 'pubmed',
            'term': f"{author}[Author]",
            'retmax': max_results,
            'retmode': 'json'
        }
        
        search_data = self._make_request(self.esearch_url, search_params)
        
        # Extract PMIDs
        id_list = search_data.get('esearchresult', {}).get('idlist', []) if search_data else []
        if not id_list:
            return []
        
        # Step 2: Get metadata for all articles
        self._rate_limit()
        summary_params = {
            'db': 'pubmed',
            'id': ','.join(id_list),
            'retmode': 'json'
        }
        
        summary_data = self._make_request(self.esummary_url, summary_params)
        if not summary_data:
            return []
        
        results = []
        for pmid in id_list:
            article = summary_data.get('result', {}).get(str(pmid), {})
            if article:
                pub = self._parse_response(article, pmid)
                if pub:
                    results.append(pub)
        
        return results
    
    def _parse_response(self, article: Dict, pmid: str) -> Publication:
        """Parse PubMed API response into Publication object."""
        # Parse authors
        authors = []
        for author_data in article.get('authors', []):
            name = author_data.get('name', '')
            if name:
                # PubMed format: "Surname Initials" → "Surname, Initials"
                parts = name.split()
                if len(parts) >= 2:
                    surname = parts[0]
                    initials = ' '.join(parts[1:])
                    authors.append(f"{surname}, {initials}")
                else:
                    authors.append(name)
        
        # Extract year from publication date
        pub_date = article.get('pubdate', '')
        year = pub_date.split()[0] if pub_date else 'n.d.'
        
        # Extract journal
        journal = article.get('fulljournalname', '') or article.get('source', '')
        
        # Extract volume, issue, pages
        volume = article.get('volume', '')
        issue = article.get('issue', '')
        pages = article.get('pages', '')
        
        # Extract DOI from article IDs
        doi = ''
        for article_id in article.get('articleids', []):
            if article_id.get('idtype') == 'doi':
                doi = article_id.get('value', '')
                break
        
        return Publication(
            source="pubmed",
            pub_type="journal-article",
            authors=authors,
            year=year,
            title=article.get('title', 'NO TITLE'),
            journal=journal,
            publisher="",
            location="",
            volume=volume,
            issue=issue,
            pages=pages,
            doi=doi
        )