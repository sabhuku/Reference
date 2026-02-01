"""API client classes for external services."""
import logging
import time
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
        results = self.search(query, rows)
        return results[0] if results else None
    
    @api_error_handler
    def search(self, query: str, rows: int = 5, year_from: Optional[int] = None, 
               year_to: Optional[int] = None, doc_type: Optional[str] = None) -> List[Publication]:
        """Search for publications with optional filters."""
        params = {
            "query.bibliographic": query,
            "rows": rows,
            "mailto": self.mailto
        }
        
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
        results = self.search(query, max_results)
        return results[0] if results else None

    @api_error_handler
    def search(self, query: str, max_results: int = 5, language: Optional[str] = None) -> List[Publication]:
        """Search for books with optional filters."""
        params = {
            "q": query,
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


class PubMedAPI:
    """PubMed E-utilities API client for biomedical literature."""
    
    def __init__(self):
        self.esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        self.esummary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Enforce NCBI rate limit of 3 requests/second."""
        elapsed = time.time() - self.last_request_time
        if elapsed < 0.34:  # 0.34s = ~3 requests/second
            time.sleep(0.34 - elapsed)
        self.last_request_time = time.time()
    
    @api_error_handler
    def search_single(self, query: str) -> Optional[Publication]:
        """Search PubMed for a single article."""
        results = self.search(query, max_results=1)
        return results[0] if results else None

    @api_error_handler
    def search(self, query: str, max_results: int = 5, year_from: Optional[int] = None, 
               year_to: Optional[int] = None, language: Optional[str] = None, 
               open_access: bool = False) -> List[Publication]:
        """Search PubMed for articles with optional filters."""
        # Step 1: Search for articles
        self._rate_limit()
        
        # Build search term with filters
        search_term = query
        
        if language:
            # PubMed uses full language names typically, but code supports standard iso codes? 
            # Actually PubMed supports 'english[lang]', 'french[lang]'. 
            # We'll map common codes or just pass through if unsure.
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
        
        try:
            search_response = requests.get(
                self.esearch_url,
                params=search_params,
                timeout=10
            )
            search_response.raise_for_status()
            search_data = search_response.json()
            
            # Extract PMID from results
            id_list = search_data.get('esearchresult', {}).get('idlist', [])
            if not id_list:
                logging.info(f"No PubMed results for: {query}")
                return []
            
            # Step 2: Get article metadata
            self._rate_limit()
            summary_params = {
                'db': 'pubmed',
                'id': ",".join(id_list),
                'retmode': 'json'
            }
            
            summary_response = requests.get(
                self.esummary_url,
                params=summary_params,
                timeout=10
            )
            summary_response.raise_for_status()
            summary_data = summary_response.json()
            
            results = []
            for pmid in id_list:
                # Extract article metadata
                article = summary_data.get('result', {}).get(str(pmid), {})
                if article:
                     pub = self._parse_response(article, pmid)
                     if pub:
                         results.append(pub)
            return results
        except Exception as e:
            logging.error(f"Error searching PubMed: {e}")
            return []
    
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
        
        try:
            search_response = requests.get(
                self.esearch_url,
                params=search_params,
                timeout=10
            )
            search_response.raise_for_status()
            search_data = search_response.json()
            
            # Extract PMIDs
            id_list = search_data.get('esearchresult', {}).get('idlist', [])
            if not id_list:
                return []
            
            # Step 2: Get metadata for all articles
            self._rate_limit()
            summary_params = {
                'db': 'pubmed',
                'id': ','.join(id_list),
                'retmode': 'json'
            }
            
            summary_response = requests.get(
                self.esummary_url,
                params=summary_params,
                timeout=10
            )
            summary_response.raise_for_status()
            summary_data = summary_response.json()
            
            results = []
            for pmid in id_list:
                article = summary_data.get('result', {}).get(str(pmid), {})
                if article:
                    pub = self._parse_response(article, pmid)
                    if pub:
                        results.append(pub)
            
            return results
            
        except Exception as e:
            logging.error(f"Error searching PubMed for author: {e}")
            return []
    
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