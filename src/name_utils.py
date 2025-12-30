"""
Name parsing and matching utilities.
"""
import unicodedata
from difflib import SequenceMatcher
from typing import Tuple

def normalize_for_comparison(text: str) -> str:
    """
    Normalize text for comparison by removing accents/diacritics and converting to lowercase.
    
    Examples:
        "José" -> "jose"
        "Müller" -> "muller"
        "García" -> "garcia"
    """
    if not text:
        return ""
    # Normalize to NFD (decomposed form) to separate base characters from diacritics
    nfd = unicodedata.normalize('NFD', text)
    # Filter out combining characters (diacritics)
    without_accents = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    return without_accents.lower()

def strings_similar(s1: str, s2: str, threshold: float = 0.85) -> bool:
    """
    Check if two strings are similar using fuzzy matching.
    
    Args:
        s1: First string
        s2: Second string  
        threshold: Similarity threshold (0.0 to 1.0). Default 0.85 means 85% similar.
    
    Returns:
        True if strings are similar enough (handles typos)
    """
    if not s1 or not s2:
        return False
    
    # Exact match is always similar
    if s1 == s2:
        return True
    
    # Use SequenceMatcher for fuzzy comparison
    ratio = SequenceMatcher(None, s1, s2).ratio()
    return ratio >= threshold

def looks_like_initial(token: str) -> bool:
    t = token.strip().replace(".", "")
    return len(t) == 1 and t.isalpha()

def guess_first_last_from_author_query(author_name: str) -> Tuple[str, str]:
    # Split on whitespace but preserve hyphens within words (e.g., "Smith-Jones" stays as one token)
    parts = author_name.strip().split()
    n = len(parts)

    # common particles in multi-word surnames
    particles = {
        "van", "von", "der", "den", "ter", "ten",
        "de", "del", "della", "di", "da", "dos", "du",
        "la", "le", "lo", "las", "los"
    }

    if n == 0:
        return "", ""

    if n == 1:
        # surname-only mode (could be hyphenated like "Smith-Jones")
        return parts[0], parts[0]

    if n == 2:
        a, b = parts[0], parts[1]
        if looks_like_initial(a) and not looks_like_initial(b):
            return a, b   # "s ruvinga"
        if looks_like_initial(b) and not looks_like_initial(a):
            return b, a   # "ruvinga s"
        return a, b       # "Stenford Ruvinga" or "John Smith-Jones"

    # n >= 3
    first_token = parts[0]
    last_token = parts[-1]

    # layout (B): "de la Cruz J" -> first="J", last="de la Cruz"
    if looks_like_initial(last_token):
        return last_token, " ".join(parts[:-1])

    # layout (A): "Juan Carlos de la Cruz"
    surname_tokens_rev = []
    i = n - 1
    surname_tokens_rev.append(parts[i])
    i -= 1
    while i >= 0:
        token = parts[i]
        if token.lower() in particles or token.islower():
            surname_tokens_rev.append(token)
            i -= 1
        else:
            break
    surname_tokens = list(reversed(surname_tokens_rev))
    target_last = " ".join(surname_tokens)
    target_first = " ".join(parts[0:i+1]).strip()
    # If we consumed all tokens as part of the surname, leave first name empty
    if target_first == "":
        target_first = ""
    return target_first, target_last

def names_match(target_first: str, target_last: str, author_given: str, author_family: str) -> bool:
    """
    Check if target name matches author name with accent-insensitive and fuzzy comparison.
    
    Supports:
    - Accent/diacritic normalization (José matches Jose)
    - Fuzzy surname matching for typos (Christoper matches Christopher)
    - Surname-only matching
    - Initial matching
    """
    if not author_family:
        return False

    # Normalize for accent-insensitive comparison
    tf = normalize_for_comparison(target_first or "")
    tl = normalize_for_comparison(target_last or "")
    ag = normalize_for_comparison(author_given or "")
    af = normalize_for_comparison(author_family or "")

    # Check surname match: exact or fuzzy (for typos)
    surname_matches = (af == tl) or strings_similar(af, tl, threshold=0.85)
    
    if not surname_matches:
        return False

    # surname-only mode
    surname_only = (tf == "" or tf == tl)
    if surname_only:
        return True

    # else require first-name / initial compatibility (with fuzzy matching)
    # Exact match or starts with
    if ag.startswith(tf):
        return True
    # Fuzzy match for typos in given name
    if strings_similar(ag, tf, threshold=0.85):
        return True
    # allow initial match only when target_first is an initial
    if len(tf) == 1 and ag[:1] == tf[:1]:
        return True

    return False
