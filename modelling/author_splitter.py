
import re

def split_authors(author_str: str) -> list[str]:
    """
    Deterministically splits an author string into a list of individual authors.
    
    Strategy:
    1. Primary splitting on SAFE delimiters (" and ", " & ", ";").
    2. Conservative comma handling: 
       - Splits by comma but recombines "Surname, Initial" pairs.
       - "Initial" is defined as starting with Uppercase followed by dots, hyphens, or other uppercase letters, 
         excluding lowercase (so "John" is treated as separate/ambiguous, but "J." is atomic).
    
    Args:
        author_str: The extracted author text (e.g., "Hochreiter, S. and Schmidhuber, J.").
        
    Returns:
        List of clean author strings.
    """
    if not author_str:
        return []

    # 1. Primary splitting (SAFE delimiters)
    # Split on " and ", " & ", " ; " (or just ;)
    # We use regex to handle variable whitespace
    chunks = re.split(r"\s+(?:and|&)\s+|;", author_str)
    
    final_authors = []
    
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
            
        # 3. Comma handling (CONSERVATIVE)
        comma_parts = chunk.split(',')
        if len(comma_parts) == 1:
            final_authors.append(chunk)
            continue
            
        recombined = []
        skip_next = False
        
        for i in range(len(comma_parts)):
            if skip_next:
                skip_next = False
                continue
                
            current = comma_parts[i].strip()
            
            # Check if there is a next part to potentially combine with
            if i + 1 < len(comma_parts):
                next_part = comma_parts[i+1].strip()
                
                # Check if next_part looks like initials
                # Allowed: "J.", "J", "J.K.", "J-P.", "A. B."
                # Disallowed: "John", "Smith" (contain lowercase letters after first char)
                # Regex logic: Starts with Upper, contains check for lowercase
                # If it has lowercase, it's likely a full name, so we don't combine (conservative)
                has_lowercase = bool(re.search(r"[a-z]", next_part))
                
                if not has_lowercase and len(next_part) > 0:
                     # It's indistinguishable from initials or a surname in all caps,
                     # but standard inverted format "Surname, I." is overwhelmingly common.
                     # We combine.
                     recombined.append(f"{current}, {next_part}")
                     skip_next = True
                else:
                    # It has lowercase letters ("John"), so treat as separate entity 
                    # (Over-split is preferred to under-split merging of two surnames)
                    recombined.append(current)
            else:
                # Last part
                recombined.append(current)
        
        final_authors.extend(recombined)

    # 4. Final Cleanup
    return [a.strip() for a in final_authors if a.strip()]

# TEST CASES
if __name__ == "__main__":
    test_cases = [
        "Hochreiter, S. and Schmidhuber, J.",
        "Smith, J.; Doe, A.",
        "Brown and White",
        "Smith, J., Doe, A."
    ]
    
    print("--- Author Splitter Tests ---\n")
    
    for t in test_cases:
        result = split_authors(t)
        print(f"Input:  '{t}'")
        print(f"Output: {result}")
        print("Reason: ", end="")
        if " and " in t and "," in t:
             print("Split on 'and', preserved 'Surname, I.' via comma logic.")
        elif ";" in t:
             print("Split on ';', preserved 'Surname, I.' via comma logic.")
        elif " and " in t:
             print("Split on 'and' only.")
        elif "," in t:
             print("Conservative comma recombination detected initials 'J.' and 'A.'.")
        print("-" * 30)
