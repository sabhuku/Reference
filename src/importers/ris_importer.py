"""RIS Importer for academic reference managers."""
import re
from typing import List, Dict
from ..models import Publication
from .base import ReferenceImporter

class RISImporter(ReferenceImporter):
    """
    Parses RIS (Research Information Systems) files.
    Common format for EndNote, Zotero, Mendeley.
    """
    
    def parse(self, content: str) -> List[Publication]:
        publications = []
        current_entry = {}
        
        # Split by lines
        lines = content.splitlines()
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # TAG  - Value format
            # e.g. "TY  - JOUR"
            match = re.match(r'^([A-Z0-9]{2})\s+-(?:\s+(.*))?$', line)
            if match:
                tag = match.group(1)
                value = match.group(2) or ""
                
                if tag == 'ER':
                    # End of record
                    if current_entry:
                        pub = self._convert_ris_to_pub(current_entry)
                        if pub:
                            publications.append(pub)
                    current_entry = {}
                elif tag == 'TY':
                    # Start of new record
                    current_entry['TY'] = value
                else:
                    # Accumulate values. Note: Some tags like AU can appear multiple times.
                    if tag in current_entry:
                        if isinstance(current_entry[tag], list):
                            current_entry[tag].append(value)
                        else:
                            current_entry[tag] = [current_entry[tag], value]
                    else:
                        # For AU (Authors), always start as list to be safe? 
                        # Or just handle list conversion later. 
                        # Standard RIS parser usually lists tags.
                        if tag in ['AU', 'A1', 'A2', 'KW']:
                            current_entry[tag] = [value]
                        else:
                            current_entry[tag] = value
                            
        # Handle case where file doesn't end with ER or last entry missing ER
        if current_entry and 'TY' in current_entry:
             pub = self._convert_ris_to_pub(current_entry)
             if pub:
                 publications.append(pub)
                 
        return publications

    def _convert_ris_to_pub(self, ris: Dict) -> Publication:
        """Map RIS tags to Publication model."""
        
        # Authors
        authors = []
        for tag in ['AU', 'A1', 'A2']:
            val = ris.get(tag, [])
            if isinstance(val, list):
                authors.extend(val)
            elif isinstance(val, str) and val:
                authors.append(val)
                
        # Type mapping
        ris_type = ris.get('TY', '').upper()
        pub_type = 'unknown'
        if ris_type == 'JOUR': pub_type = 'journal-article'
        elif ris_type == 'BOOK': pub_type = 'book'
        elif ris_type == 'CHAP': pub_type = 'book-chapter'
        elif ris_type in ['CONF', 'CPAPER']: pub_type = 'proceedings-article'
        elif ris_type in ['THES']: pub_type = 'thesis'
        elif ris_type in ['RPRT']: pub_type = 'report'
        elif ris_type in ['ELEC', 'WEB']: pub_type = 'website'
        
        # Date/Year
        # PY = Publication Year, Y1 = Primary Date
        year = ris.get('PY', ris.get('Y1', ''))
        if isinstance(year, list): year = year[0] # Take first if multiple
        # Extract 4 digit year if possible
        year_match = re.search(r'\d{4}', str(year))
        clean_year = year_match.group(0) if year_match else str(year)

        return Publication(
            source='import (ris)',
            pub_type=pub_type,
            authors=authors,
            year=clean_year,
            title=self._get_str(ris, ['TI', 'T1', 'ST']), # Title tags
            journal=self._get_str(ris, ['JO', 'JF', 'JA']), # Journal tags
            publisher=self._get_str(ris, ['PB']),
            location=self._get_str(ris, ['CY', 'PP']), # City/Place
            volume=self._get_str(ris, ['VL']),
            issue=self._get_str(ris, ['IS']),
            pages=self._get_str(ris, ['SP', 'EP']), # Start/End page usually logic needed, but SP often holds full range in simple exports
            doi=self._get_str(ris, ['DO'])
        )

    def _get_str(self, ris: Dict, tags: List[str]) -> str:
        """Helper to get first available string content from list of tags."""
        for tag in tags:
            val = ris.get(tag)
            if val:
                if isinstance(val, list):
                    return str(val[0])
                return str(val)
        return ""
