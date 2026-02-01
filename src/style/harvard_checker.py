"""Harvard style checker implementation."""
import re
from typing import List, Optional

from ..models import Publication
from .models import Violation, Severity

class HarvardStyleChecker:
    """Validates publications against Harvard style rules."""
    
    def check_publications(self, publications: List[Publication]) -> List[List[Violation]]:
        """
        Check a list of publications.
        Returns a list of violation lists, corresponding to the input list.
        """
        all_violations = []
        for index, pub in enumerate(publications):
            all_violations.append(self.check_single(pub, index))
        return all_violations

    def check_single(self, pub: Publication, index: int = -1) -> List[Violation]:
        """Check a single publication against all rules."""
        violations = []
        
        # 0. Normalization Feedback (Info level, non-punitive)
        if pub.normalization_log:
            for log in pub.normalization_log:
                violations.append(Violation(
                    rule_id="NORMALIZATION.INFO",
                    severity="info",
                    message=log,
                    field_name="general",
                    reference_id=None # Set by reporter
                ))
        
        # Apply all rules
        for rule in [
            self._check_author_missing,
            self._check_author_format,
            self._check_year_missing,
            self._check_title_missing,
            self._check_title_capitalization,
            self._check_journal_missing,
            self._check_book_publisher,
            self._check_book_location,
            self._check_journal_details,
            self._check_doi_url,
            self._check_web_details,
            self._check_edition_info,
            self._check_conference_details
        ]:
            v = rule(pub)
            if v:
                violations.append(v)
                
        return violations

    # --- Rules ---

    def _check_author_missing(self, pub: Publication) -> Optional[Violation]:
        """HARVARD.AUTHOR.MISSING: Reference must have at least one author."""
        # Use normalized_authors if populated, else fallback to raw authors
        auths = pub.normalized_authors if pub.normalized_authors else pub.authors
        if not auths:
            return Violation(
                rule_id="HARVARD.AUTHOR.MISSING",
                severity="warning",
                message="Reference is missing author(s). Check if this field was parsed correctly.",
                field_name="authors"
            )
        return None

    def _check_author_format(self, pub: Publication) -> Optional[Violation]:
        """HARVARD.AUTHOR.FORMAT: Authors should be 'Surname, I.' or 'Surname, Name'."""
        auths = pub.normalized_authors if pub.normalized_authors is not None else pub.authors
        if not auths:
            return None
            
        for auth in auths:
            if "," not in auth:
                 return Violation(
                    rule_id="HARVARD.AUTHOR.FORMAT",
                    severity="warning",
                    message=f"Author '{auth}' should be formatted as 'Surname, Initial(s)' (missing comma).",
                    field_name="authors"
                )
        return None

    def _check_year_missing(self, pub: Publication) -> Optional[Violation]:
        """HARVARD.YEAR.MISSING: Year is required."""
        # Check explicit year_status if present
        if hasattr(pub, 'year_status'):
             if pub.year_status == 'missing':
                 return Violation(
                    rule_id="HARVARD.YEAR.MISSING",
                    severity="warning",
                    message="Publication year is missing or unparsable.",
                    field_name="year"
                )
             if pub.year_status == 'explicitly_undated':
                 # 'explicitly_undated' (n.d.) is acceptable in Harvard
                 return None
             
        # Fallback for non-normalized OR 'present' status but empty value
        if not pub.year:
            return Violation(
                rule_id="HARVARD.YEAR.MISSING",
                severity="warning",
                message="Publication year is missing.",
                field_name="year"
            )
        return None

    def _check_title_missing(self, pub: Publication) -> Optional[Violation]:
        """HARVARD.TITLE.MISSING: Title is required."""
        if not pub.title:
            return Violation(
                rule_id="HARVARD.TITLE.MISSING",
                severity="warning",
                message="Work title is missing.",
                field_name="title"
            )
        return None

    def _check_title_capitalization(self, pub: Publication) -> Optional[Violation]:
        """HARVARD.TITLE.CAPITALIZATION: Info only for capitalization suggestions."""
        if not pub.title:
            return None
            
        if pub.title.isupper() and len(pub.title) > 4: 
             return Violation(
                rule_id="HARVARD.TITLE.CAPITALIZATION",
                severity="info",
                message="Title is in ALL CAPS. Consider converting to sentence case.",
                field_name="title"
            )
        if pub.title.islower():
             return Violation(
                rule_id="HARVARD.TITLE.CAPITALIZATION",
                severity="info",
                message="Title is all lowercase. Consider capitalizing first letter and proper nouns.",
                field_name="title"
            )
        return None

    def _check_journal_missing(self, pub: Publication) -> Optional[Violation]:
        """HARVARD.JOURNAL.MISSING: Articles must have journal name."""
        if self._is_article(pub) and not pub.journal:
             return Violation(
                rule_id="HARVARD.JOURNAL.MISSING",
                severity="error",
                message="Journal articles must include the journal name.",
                field_name="journal"
            )
        return None

    def _check_book_publisher(self, pub: Publication) -> Optional[Violation]:
        """HARVARD.BOOK.PUBLISHER_MISSING: Books must have publisher."""
        if self._is_book(pub) and not pub.publisher:
             return Violation(
                rule_id="HARVARD.BOOK.PUBLISHER_MISSING",
                severity="error",
                message="Books must include the publisher name.",
                field_name="publisher"
            )
        return None

    def _check_book_location(self, pub: Publication) -> Optional[Violation]:
        """HARVARD.BOOK.LOCATION_MISSING: Books should have location."""
        if self._is_book(pub) and not pub.location:
             return Violation(
                rule_id="HARVARD.BOOK.LOCATION_MISSING",
                severity="warning",
                message="Books should include the place of publication (City).",
                field_name="location"
            )
        return None

    def _check_journal_details(self, pub: Publication) -> Optional[Violation]:
        """HARVARD.JOURNAL.DETAILS_MISSING: Articles need Vol, Issue, Pages."""
        if self._is_article(pub):
            # Relaxed for newspapers
            newspaper_keywords = ["guardian", "times", "independent", "telegraph", "sun", "mirror", "daily", "news"]
            source_lower = (pub.journal or "").lower()
            if any(kw in source_lower for kw in newspaper_keywords):
                return None
            
            # Relaxed if date looks like a specific day (e.g. "18 August")
            if pub.journal and re.search(r'\d+\s+[A-Z][a-z]+', pub.journal):
                return None

            missing = []
            if not pub.volume: missing.append("volume")
            # Relaxed: Issue is often optional in modern Harvard if Volume exists, but we can verify prompt preference? 
            # Prompt says "Mandatory fields vary by source type... Optional but recommended fields = Warnings".
            # Standard Harvard usually wants both if available.
            if not pub.pages: missing.append("pages")
            
            if missing:
                return Violation(
                    rule_id="HARVARD.JOURNAL.DETAILS_MISSING",
                    severity="warning",
                    message=f"Article reference is missing details: {', '.join(missing)}.",
                    field_name="pages" 
                )
        return None

    def _check_doi_url(self, pub: Publication) -> Optional[Violation]:
        """HARVARD.DOI_OR_URL.MISSING: Articles should have DOI/URL."""
        # Info level only.
        if self._is_article(pub) and not pub.doi:
             return Violation(
                rule_id="HARVARD.DOI_OR_URL.MISSING",
                severity="info",
                message="Consider adding a DOI for digital journal articles.",
                field_name="doi"
            )
        return None

    def _check_web_details(self, pub: Publication) -> Optional[Violation]:
        """HARVARD.WEB.DETAILS_MISSING: Web references need URL and Access Date."""
        web_types = ["webpage", "photograph", "instagram", "online image", "forum-post", "module-material"]
        if pub.pub_type in web_types or pub.url:
            missing = []
            if not pub.url: missing.append("URL")
            if not pub.access_date: missing.append("access date")
            
            if missing:
                return Violation(
                    rule_id="HARVARD.WEB.DETAILS_MISSING",
                    severity="warning",
                    message=f"Online reference is missing: {', '.join(missing)}.",
                    field_name="url"
                )
        return None

    # --- Helpers ---
    
    def _is_article(self, pub: Publication) -> bool:
        """Determine if publication is a journal article."""
        # Mutually exclusive with book and conference
        if self._is_book(pub) or self._is_conference(pub):
            return False
            
        t = pub.pub_type.lower() if pub.pub_type else ""
        return "article" in t or "journal" in t or bool(pub.journal)

    def _is_book(self, pub: Publication) -> bool:
        """Determine if publication is a book."""
        t = pub.pub_type.lower() if pub.pub_type else ""
        # Explicit book or chapter is a book-like entity for metadata rules
        return ("book" in t or "chapter" in t) and "article" not in t and "web" not in t

    def _check_edition_info(self, pub: Publication) -> Optional[Violation]:
        """HARVARD.BOOK.EDITION_INFO: Books should include edition if not first edition."""
        # INFO level only - edition is recommended but not always required
        # Only suggest for print books (not e-books which may not have editions)
        if self._is_book(pub) and not pub.edition and not pub.url:
            return Violation(
                rule_id="HARVARD.BOOK.EDITION_INFO",
                severity="info",
                message="Consider adding edition information if this is not the first edition.",
                field_name="edition"
            )
        return None

    def _is_conference(self, pub: Publication) -> bool:
        """Determine if publication is a conference paper."""
        t = pub.pub_type.lower() if pub.pub_type else ""
        return "conference" in t or "proceedings" in t

    def _check_conference_details(self, pub: Publication) -> Optional[Violation]:
        """HARVARD.CONFERENCE.DETAILS_MISSING: Conference papers need name, location, pages."""
        if self._is_conference(pub):
            missing = []
            if not pub.conference_name: missing.append("conference name")
            if not pub.conference_location: missing.append("location")
            if not pub.pages: missing.append("pages")
            
            if missing:
                return Violation(
                    rule_id="HARVARD.CONFERENCE.DETAILS_MISSING",
                    severity="warning",
                    message=f"Conference paper is missing: {', '.join(missing)}.",
                    field_name="conference_name"
                )
        return None
