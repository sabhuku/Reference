"""
Tier 0 Deterministic Fixes - Week 3 Implementation

100% deterministic, safe auto-fixes that require NO AI.
These fixes are applied automatically with user approval.
"""
import re
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Tier0Fix:
    """Result of a Tier 0 fix."""
    field: str
    old_value: str
    new_value: str
    fix_type: str
    description: str


class DeterministicFixer:
    """
    Tier 0 deterministic fixes (NO AI).
    
    These fixes are:
    - 100% deterministic (same input → same output)
    - Safe (no data loss)
    - Conservative (only fix obvious issues)
    - Fast (<10ms per reference)
    """
    
    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """
        Remove extra whitespace.
        
        Examples:
            "The  Great   Gatsby" → "The Great Gatsby"
            "  Leading spaces  " → "Leading spaces"
        """
        if not text:
            return text
        
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    @staticmethod
    def fix_double_periods(text: str) -> str:
        """
        Remove double periods.
        
        Examples:
            "Oxford Univ. Press.." → "Oxford Univ. Press."
            "Vol. 5.." → "Vol. 5."
        """
        if not text:
            return text
        
        # Replace multiple periods with single period
        text = re.sub(r'\.\.+', '.', text)
        
        return text
    
    @staticmethod
    def fix_double_commas(text: str) -> str:
        """
        Remove double commas.
        
        Examples:
            "Smith,, John" → "Smith, John"
        """
        if not text:
            return text
        
        # Replace multiple commas with single comma
        text = re.sub(r',,+', ',', text)
        
        return text
    
    @staticmethod
    def normalize_year(year: str) -> Optional[str]:
        """
        Normalize year format.
        
        Examples:
            " 2023 " → "2023"
            "2023." → "2023"
        """
        if not year:
            return year
        
        # Remove whitespace
        year = year.strip()
        
        # Remove trailing period
        year = year.rstrip('.')
        
        # Validate 4-digit year
        if year.isdigit() and len(year) == 4:
            year_int = int(year)
            if 1000 <= year_int <= 2100:
                return year
        
        return None  # Invalid year
    
    @staticmethod
    def normalize_pages(pages: str) -> str:
        """
        Normalize page range format.
        
        Examples:
            "123 - 456" → "123-456"
            "pp. 123-456" → "123-456"
            "p.123" → "123"
        """
        if not pages:
            return pages
        
        # Remove "pp." or "p." prefix
        pages = re.sub(r'^pp?\.\s*', '', pages, flags=re.IGNORECASE)
        
        # Normalize spaces around dash
        pages = re.sub(r'\s*-\s*', '-', pages)
        
        # Remove extra whitespace
        pages = pages.strip()
        
        return pages
    
    @staticmethod
    def apply_tier0_fixes(reference: dict) -> Dict[str, any]:
        """
        Apply all Tier 0 fixes to a reference.
        
        Args:
            reference: Reference dictionary
        
        Returns:
            {
                'patches': [...],  # JSON patch operations
                'fixes': [...],    # List of Tier0Fix objects
                'fields_modified': [...],
                'tier': 'tier_0',
                'rationale': '...'
            }
        """
        patches = []
        fixes = []
        
        # Fix 1: Normalize whitespace in title
        if reference.get('title'):
            old_title = reference['title']
            new_title = DeterministicFixer.normalize_whitespace(old_title)
            new_title = DeterministicFixer.fix_double_periods(new_title)
            
            if old_title != new_title:
                patches.append({
                    'op': 'replace',
                    'path': '/title',
                    'value': new_title
                })
                fixes.append(Tier0Fix(
                    field='title',
                    old_value=old_title,
                    new_value=new_title,
                    fix_type='whitespace_normalization',
                    description='Normalized whitespace and removed double periods'
                ))
        
        # Fix 2: Normalize whitespace in publisher
        if reference.get('publisher'):
            old_publisher = reference['publisher']
            new_publisher = DeterministicFixer.normalize_whitespace(old_publisher)
            new_publisher = DeterministicFixer.fix_double_periods(new_publisher)
            
            if old_publisher != new_publisher:
                patches.append({
                    'op': 'replace',
                    'path': '/publisher',
                    'value': new_publisher
                })
                fixes.append(Tier0Fix(
                    field='publisher',
                    old_value=old_publisher,
                    new_value=new_publisher,
                    fix_type='whitespace_normalization',
                    description='Normalized whitespace'
                ))
        
        # Fix 3: Normalize whitespace in journal
        if reference.get('journal'):
            old_journal = reference['journal']
            new_journal = DeterministicFixer.normalize_whitespace(old_journal)
            new_journal = DeterministicFixer.fix_double_periods(new_journal)
            
            if old_journal != new_journal:
                patches.append({
                    'op': 'replace',
                    'path': '/journal',
                    'value': new_journal
                })
                fixes.append(Tier0Fix(
                    field='journal',
                    old_value=old_journal,
                    new_value=new_journal,
                    fix_type='whitespace_normalization',
                    description='Normalized whitespace'
                ))
        
        # Fix 4: Normalize year
        if reference.get('year'):
            old_year = reference['year']
            new_year = DeterministicFixer.normalize_year(old_year)
            
            if new_year and old_year != new_year:
                patches.append({
                    'op': 'replace',
                    'path': '/year',
                    'value': new_year
                })
                fixes.append(Tier0Fix(
                    field='year',
                    old_value=old_year,
                    new_value=new_year,
                    fix_type='year_normalization',
                    description='Normalized year format'
                ))
        
        # Fix 5: Normalize pages
        if reference.get('pages'):
            old_pages = reference['pages']
            new_pages = DeterministicFixer.normalize_pages(old_pages)
            
            if old_pages != new_pages:
                patches.append({
                    'op': 'replace',
                    'path': '/pages',
                    'value': new_pages
                })
                fixes.append(Tier0Fix(
                    field='pages',
                    old_value=old_pages,
                    new_value=new_pages,
                    fix_type='page_normalization',
                    description='Normalized page range format'
                ))
        
        # Build rationale
        if fixes:
            fix_descriptions = [f"{f.field}: {f.description}" for f in fixes]
            rationale = f"Tier 0 deterministic fixes: {'; '.join(fix_descriptions)}"
        else:
            rationale = "No Tier 0 fixes needed"
        
        return {
            'patches': patches,
            'fixes': [
                {
                    'field': f.field,
                    'old_value': f.old_value,
                    'new_value': f.new_value,
                    'fix_type': f.fix_type,
                    'description': f.description
                }
                for f in fixes
            ],
            'fields_modified': [p['path'][1:] for p in patches],
            'tier': 'tier_0',
            'rationale': rationale,
            'confidence_scores': {p['path'][1:]: 1.0 for p in patches}  # Deterministic = 100% confidence
        }


# Example usage
if __name__ == '__main__':
    # Test reference with formatting issues
    test_ref = {
        'title': 'The  Great   Gatsby..',
        'publisher': '  Oxford University  Press  ',
        'journal': 'Nature  Biotechnology..',
        'year': ' 2023. ',
        'pages': 'pp. 123 - 456'
    }
    
    result = DeterministicFixer.apply_tier0_fixes(test_ref)
    
    print("Tier 0 Fixes Applied:")
    print(f"Patches: {len(result['patches'])}")
    print(f"Fields modified: {result['fields_modified']}")
    print(f"Rationale: {result['rationale']}")
    print()
    
    for fix in result['fixes']:
        print(f"  {fix['field']}:")
        print(f"    Old: '{fix['old_value']}'")
        print(f"    New: '{fix['new_value']}'")
        print(f"    Type: {fix['fix_type']}")
        print()
