"""Base class for reference importers."""
from abc import ABC, abstractmethod
from typing import List
from ..models import Publication

class ReferenceImporter(ABC):
    """Abstract base class for importing references from files."""
    
    @abstractmethod
    def parse(self, content: str) -> List[Publication]:
        """Parse string content into a list of Publications."""
        pass
