import re

# Test edition pattern
text = "Pfleeger, C. P. and Pfleeger, S. L.(2006) Security in computing. 4th edn. Upper Saddle River,NJ: Prentice Hall."

edition_pattern = re.compile(r'(\d+(?:st|nd|rd|th)\s+edn?\.?)', re.IGNORECASE)
edition_match = edition_pattern.search(text)

if edition_match:
    print(f"Found: '{edition_match.group(1)}'")
else:
    print("NOT FOUND")
    
# Try alternative patterns
patterns = [
    r'(\d+(?:st|nd|rd|th)\s+edn?\.?)',
    r'(\d+(?:st|nd|rd|th)\s+ed(?:n|ition)?\.?)',
    r'\.?\s*(\d+(?:st|nd|rd|th)\s+edn?\.?)\s',
]

for i, pat in enumerate(patterns, 1):
    match = re.search(pat, text, re.IGNORECASE)
    print(f"Pattern {i}: {match.group(1) if match else 'NO MATCH'}")
