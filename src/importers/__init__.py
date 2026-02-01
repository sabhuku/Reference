from .base import ReferenceImporter
from .json_importer import JSONImporter
from .ris_importer import RISImporter
from .docx_importer import DocxImporter

def get_importer_for_file(filename: str) -> ReferenceImporter:
    """Factory to get appropriate importer based on extension."""
    ext = filename.lower().split('.')[-1]
    if ext == 'json':
        return JSONImporter()
    elif ext in ['ris', 'txt']:
        # .txt often used for RIS exports too
        return RISImporter()
    elif ext in ['docx', 'doc']:
        return DocxImporter()
    else:
        # Default fallback or error?
        # For now return JSON as fallback or None
        return JSONImporter()
