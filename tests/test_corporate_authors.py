
import unittest
from dataclasses import dataclass
from typing import List

# Minimal mock for testing
@dataclass
class Publication:
    authors: List[str]
    normalized_authors: List[str] = None
    authors_inferred: bool = False
    normalization_log: List[str] = None
    title: str = ""
    year: str = ""
    year_status: str = ""
    pub_type: str = ""
    source_type_inferred: bool = False

    def __post_init__(self):
        if self.normalized_authors is None: self.normalized_authors = []
        if self.normalization_log is None: self.normalization_log = []

# Assuming the updated ReferenceNormalizer is available appropriately. 
import sys
import os

# Create a mock for .models
from dataclasses import dataclass
@dataclass
class Publication:
    authors: List[str]
    normalized_authors: List[str] = None
    authors_inferred: bool = False
    normalization_log: List[str] = None
    title: str = ""
    year: str = ""
    year_status: str = "present"
    pub_type: str = "unknown"
    source_type_inferred: bool = False
    _normalization_done: bool = False

    def __post_init__(self):
        if self.normalized_authors is None: self.normalized_authors = []
        if self.normalization_log is None: self.normalization_log = []

# Mock the module locally
import types
models_mod = types.ModuleType("src.models")
models_mod.Publication = Publication
sys.modules["src.models"] = models_mod
# Also mock 'src' package
src_mod = types.ModuleType("src")
src_mod.models = models_mod
sys.modules["src"] = src_mod

# Now load normalizer by path
normalizer_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'normalizer.py'))
import importlib.util
spec = importlib.util.spec_from_file_location("src.normalizer", normalizer_path)
normalizer_mod = importlib.util.module_from_spec(spec)
# Need to monkeypatch the relative import in the loaded module?
# Actually if we load it as "src.normalizer", "from .models" works if "src" is a package.
# But "src" isn't fully set up.
# Let's just load it as a standalone module and patch the import line if needed, OR relies on sys.modules hack for 'models'.
# If "from .models" executes, it looks for "normalizer_pkg.models".
# Let's try simpler: exec the file content skipping the import.

with open(normalizer_path, 'r') as f:
    code = f.read()

# Remove the relative import
code = code.replace("from .models import Publication", "")

# Exec in a customized namespace
ns = {"Publication": Publication, "re": __import__("re"), "List": List, "Tuple": __import__("typing").Tuple}
exec(code, ns)
ReferenceNormalizer = ns["ReferenceNormalizer"]

class TestCorporateAuthorDetection(unittest.TestCase):
    
    def normalize(self, authors):
        pub = Publication(authors=authors)
        ReferenceNormalizer.normalize(pub)
        return pub.normalized_authors

    def test_modern_tech_companies(self):
        """Test detection of modern tech entities."""
        self.assertEqual(self.normalize(["OpenAI"]), ["OpenAI"])
        self.assertEqual(self.normalize(["DeepMind"]), ["DeepMind"])
        self.assertEqual(self.normalize(["Google"]), ["Google"])
        self.assertEqual(self.normalize(["Microsoft"]), ["Microsoft"])

    def test_traditional_corporates(self):
        """Test detection of traditional corporate entities."""
        self.assertEqual(self.normalize(["World Health Organization"]), ["World Health Organization"])
        self.assertEqual(self.normalize(["United Nations"]), ["United Nations"]) # 'united' not kw? 'nations'? 'un' is kw.
        # Wait, 'un' is in kw list now? Yes. But checking tokens.
        # "United Nations" has tokens {"united", "nations"}. "un" is NOT "united".
        # We did not add "United" or "Nations". We added "un".
        # Let's verify our list. We added 'un'.
        # "United Nations" might fail if we don't assume "United" or "Nations" are keywords.
        # But "WHO" -> tokens {"who"}. matched.
        pass

    def test_acronyms(self):
        self.assertEqual(self.normalize(["WHO"]), ["WHO"])
        self.assertEqual(self.normalize(["NASA"]), ["NASA"])
        
    def test_personal_names_prevent_false_positives(self):
        """Ensure personal names are NOT flagged as corporate."""
        # "Juan de la Cruz" -> has "de", "la" (prefixes) but not corp keywords.
        # Tokens: juan, de, la, cruz. None in CORPORATE_KEYWORDS.
        # Result: Should be parsed as name.
        # "Cruz, J." -> "Cruz, J."
        authors = self.normalize(["Juan de la Cruz"])
        # name parser converts "Juan de la Cruz" -> "de la Cruz, Juan" or similar?
        # Let's see normalizer logic. It handles prefixes.
        # It likely outputs "de la Cruz, Juan".
        self.assertIn(",", authors[0]) 

    def test_mixed_cases(self):
        # "Smith, J." -> Personal
        self.assertEqual(self.normalize(["Smith, J."]), ["Smith, J."])
        
        # "Oxford University Press" -> Corporate (contains 'university', 'press')
        self.assertEqual(self.normalize(["Oxford University Press"]), ["Oxford University Press"])

    def test_single_word_person(self):
        """Test Plato (mononym)."""
        # "Plato". Tokens {"plato"}. Not in keywords.
        # Should be treated as surname: "Plato"
        # Since logic falls through to comma check (fail) -> space check (tokens=1) -> Surname=Plato, Given=""
        # Normalizer outputs "Surname" -> "Plato"
        # It should NOT be flagged as corporate, but formatted as name (which is just "Plato").
        # The crucial bit is it shouldn't be exempted from validation checks if validation expects "Surname, I." format?
        # Or maybe it is?
        # Actually normalizer just strings it.
        # So "Plato" -> "Plato". 
        result = self.normalize(["Plato"])
        self.assertEqual(result, ["Plato"])
        
if __name__ == "__main__":
    unittest.main()
