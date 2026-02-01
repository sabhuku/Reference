"""
Reference Normalization Logic.
Ensures heterogeneous inputs are sanitized into a strict schema before validation.
"""
import re
from typing import List, Tuple
from .models import Publication

class ReferenceNormalizer:
    """
    Normalizes publications to ensure parity between input formats (JSON/RIS).
    Separates data cleaning execution from validation judgment.
    """
    
    @staticmethod
    def normalize(pub: Publication) -> Publication:
        """
        Apply strict normalization rules to a publication.
        Modifies the publication in-place.
        Idempotent: safe to call multiple times.
        """
        
        # Guard against double normalization
        # If normalized_authors is already populated and matches length of raw authors, assume done?
        # Better: check a flag or just ensure logic is idempotent.
        # But `_normalize_authors` logic (parsing "Smith, J.") handles formatted input gracefully,
        # UNLESS the logic sees "Smith, J." and parses it as Surname="Smith", Given="J." -> "Smith, J."
        # The risk is if it parses "Smith, J." as Surname="Smith", Given="J" -> "Smith, J."
        # Actually our logic does: split on comma -> surname=Smith, given=J. -> re-initial -> Smith, J.
        # So it seems idempotent? 
        # But let's be safer: if we have a normalization_log, we might be duplicating logs.
        
        if getattr(pub, '_normalization_done', False):
            return pub
            
        # 1. Author Normalization
        # Only normalize if not explicitly already normalized or if empty
        if not pub.normalized_authors:
            norm_authors, inferred_auth, logs_auth = ReferenceNormalizer._normalize_authors(pub.authors)
            pub.normalized_authors = norm_authors
            pub.authors_inferred = inferred_auth
            if logs_auth:
                pub.normalization_log.extend(logs_auth)
        
        # 2. Year Normalization
        # Only normalize if status is default/empty
        if pub.year_status == "present" and not pub.year and not pub.normalization_log:
             # This is a bit weak. Let's rely on the flag.
             pass
             
        # Full re-run logic with flag check
        clean_year, year_status, logs_year = ReferenceNormalizer._normalize_year(pub.year)
        # Only update if changed or if status is meaningful?
        # Actually, `_normalize_year` is pure. 
        pub.year = clean_year
        pub.year_status = year_status
        if logs_year:
            pub.normalization_log.extend(logs_year)
        
        # 3. Source Type Normalization
        if pub.pub_type == 'unknown':
            pub.source_type_inferred = True
            if "Source type could not be determined" not in pub.normalization_log:
                 pub.normalization_log.append("Source type could not be determined; falling back to generic handling.")
        
        # 4. Title Normalization
        if pub.title:
            pub.title = pub.title.strip()
            
        # Mark as done
        pub._normalization_done = True
            
        return pub

    @staticmethod
    def _normalize_authors(authors: List[str]) -> Tuple[List[str], bool, List[str]]:
        """
        Convert authors to "Surname, I." format.
        Handles: "John Smith", "Smith, John", "Smith J", "J. Smith", "van der Waals, J.", "GP Smith".
        """
        normalized = []
        inferred = False
        logs = []
        
        # Common surname prefixes (particles)
        # These are usually lowercase in input, but we compare lower
        PREFIXES = {'van', 'von', 'de', 'du', 'da', 'del', 'della', 'di', 'der', 'den', 'ten', 'ter', 'le', 'la', 'al', 'mc', 'mac', 'bin', 'ibn'}
        
        if not authors:
            return [], False, []
            
        # Corporate keywords - Expanded for modern organizations
        CORPORATE_KEYWORDS = {
            # Legacy
            'organization', 'university', 'institute', 'association', 
            'committee', 'council', 'commission', 'department', 'ministry', 
            'group', 'society', 'agency', 'authority', 'board', 'bureau', 
            'center', 'centre', 'college', 'corporation', 'foundation', 
            'trust', 'ltd', 'inc', 'co', 'corp',
            # Modern / Tech
            'laboratory', 'labs', 'research', 'technologies', 'technology',
            'systems', 'solutions', 'consortium', 'alliance', 'union',
            'government', 'office', 'service', 'services', 'team',
            'working', 'task', 'force', 'initiative', 'project', 'program',
            'press', 'media', 'network', 'networks', 'global', 'international',
            'national', 'royal', 'academy', 'bank', 'fund', 'observatory',
            'museum', 'library', 'hospital', 'clinic', 'school',
            # Specific Tech Entities (Heuristic)
            'openai', 'deepmind', 'google', 'meta', 'amazon', 'microsoft',
            'apple', 'facebook', 'twitter', 'uber', 'airbnb', 'netflix',
            'nvidia', 'intel', 'ibm', 'oracle', 'cisco', 'adobe', 'salesforce',
            'who', 'un', 'unesco', 'nasa', 'esa', 'cern', 'ieee', 'acm',
            'united', 'nations' # Add explicitly for "United Nations"
        }
            
        for auth_str in authors:
            auth_str = auth_str.strip()
            if not auth_str:
                continue
                
            surname = ""
            given = ""
            
            # 0. Check for Corporate Author
            lower_auth = auth_str.lower()
            
            # Function to check if it looks like a personal name structure
            def looks_like_person(s: str) -> bool:
                # "Smith, J." or "Smith, John" -> Yes
                if "," in s: return True
                
                parts = s.split()
                # "Plato" -> Yes (Single word, proper case)
                if len(parts) == 1: 
                    # If it's a known corp entity like "OpenAI", we catch it below.
                    # Otherwise, single word is ambiguous. 
                    # If it's pure alphabetical and not a known keyword, treat as person name (mononym or surname-only).
                    # But "WHO" is also single word. "DeepMind" is single word.
                    # We rely on keyword list for single words.
                    return True
                
                # "Juan de la Cruz" -> Maybe
                # "J. Smith" -> Yes (Initial dot)
                if any('.' in p and len(p.replace('.', '')) == 1 for p in parts):
                    return True
                
                # "John Smith" -> Yes
                # But "OpenAI Research" -> No
                return False

            is_corporate = False
            
            # Heuristic 1: Explicit Keyword Match
            # Split auth string into tokens to match whole words (e.g. "center" matches "Center", not "Centerline")
            # But simple substring check `kw in lower_auth` matches "Group" in "Groupon".
            # Let's tokenize.
            auth_tokens = set(re.findall(r'\w+', lower_auth))
            if not auth_tokens.isdisjoint(CORPORATE_KEYWORDS):
                is_corporate = True
                
            # Heuristic 2: Known Entity Exact/Partial Match (for multi-word specifics like "World Health Organization")
            # Covered by keywords usually ('Organization').
            
            # Heuristic 3: Structure check
            # If ANY part looks like an initial "J.", likely person.
            if any(re.match(r'^[A-Z]\.$', p) for p in auth_str.split()):
                is_corporate = False
            
            # If comma present, almost certainly personal name format "Surname, Given"
            if "," in auth_str:
                is_corporate = False
                
            if is_corporate:
                # Treat as single name, no formatting
                normalized.append(auth_str)
                continue
            
            # 1. Check comma format: "Surname, Given..."
            if "," in auth_str:
                parts = auth_str.split(",", 1)
                surname = parts[0].strip()
                given = parts[1].strip()
            # 2. Space format: "Given Surname"
            else:
                inferred = True
                tokens = auth_str.split()
                if not tokens:
                    continue
                    
                if len(tokens) == 1:
                    surname = tokens[0]
                    given = ""
                else:
                    # Detect multi-word surname via prefixes
                    # Scan backwards from second-to-last token
                    # "John van der Waals" -> tokens: John, van, der, Waals
                    # Check 'der' -> prefix? Yes. Check 'van' -> prefix? Yes.
                    
                    surname_start_idx = len(tokens) - 1
                    
                    # Iterate backwards from second to last word
                    for i in range(len(tokens) - 2, -1, -1):
                        token = tokens[i].lower().replace('.', '')
                        if token in PREFIXES:
                            surname_start_idx = i
                        else:
                            # Stop at first non-prefix
                             break
                    
                    surname = " ".join(tokens[surname_start_idx:])
                    given = " ".join(tokens[:surname_start_idx])
                    
                    logs.append(f"Inferred author structure for '{auth_str}' -> '{surname}, {given}'")

            # Format Initials
            if given:
                # Extract initials
                # Handle "A.B.", "A. B.", "AB" (if all caps), "Jean-Luc"
                initials_list = []
                
                # Split by space or dot or hyphen?
                # Standard split by space first
                g_parts = given.replace('.', ' ').split()
                
                for part in g_parts:
                    if not part: continue
                    # Hyphenated names: "Jean-Luc" -> "J-L."? Or "J.L."?
                    # Harvard usually "J.-L." or just "J." depending on strictness.
                    # We'll treat hyphenated as separate initials "J.L." per some interpretations, 
                    # or keep hyphen. Let's stick to standard "J.L." for simplicity unless requested.
                    # Actually "Jean-Luc" -> "J.-L." is common.
                    # Let's simplify: split by hyphen too?
                    
                    subparts = part.split('-')
                    part_initials = []
                    for sub in subparts:
                        if not sub: continue
                        
                        # Check if it's already an initial set like "AB" (if len < 4 and all upper?)
                        if sub.isupper() and len(sub) > 1 and len(sub) < 4:
                            # "AB" -> "A.B."
                            for char in sub:
                                if char.isalpha():
                                    part_initials.append(f"{char.upper()}.")
                        else:
                            # Just first letter
                            if sub[0].isalpha():
                                part_initials.append(f"{sub[0].upper()}.")
                    
                    if part_initials:
                         initials_list.extend(part_initials)

                formatted_initials = "".join(initials_list)
                formatted = f"{surname}, {formatted_initials}"
            else:
                formatted = surname
                
            normalized.append(formatted)
            
        return normalized, inferred, logs

    @staticmethod
    def _normalize_year(year_input: str) -> Tuple[str, str, List[str]]:
        """
        Normalize year field.
        Returns: (year_str, status_enum, logs)
        """
        y_str = str(year_input).strip().lower() if year_input else ""
        logs = []
        
        if not y_str:
            return "", "missing", []
            
        # Check for explicit "no date" markers
        if y_str in ["n.d.", "n.d", "no date", "undated"]:
            return "n.d.", "explicitly_undated", []
            
        # Extract 4-digit year + optional lowercase suffix
        # Matches "2020", "2020a", "published near 1999b"
        match = re.search(r'\d{4}[a-z]?', y_str)
        if match:
            return match.group(0), "present", []
            
        # If input exists but isn't a year or n.d. -> treat as missing or just raw text?
        # prompt says "If missing, leave empty (do NOT fabricate). If undated but explicitly stated, use n.d."
        # If we have "In Press" or something? 
        # For now, if we can't find a year, we mark as missing for validation purposes, 
        # but maybe keep the text? No, schema says "title, authors, year...". 
        # Let's return invalid string but status missing?
        # Actually safer to blank it if it's junk, or keep as is?
        # Strict normalization: if not valid year, empty it.
        logs.append(f"Could not parse year from '{year_input}'; marked as missing.")
        return "", "missing", logs
