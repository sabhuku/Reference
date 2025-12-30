from .src.referencing.referencing import (
    main,
    load_cache,
    save_cache,
    lookup_single_work,
    lookup_author_works,
    reference_entry,
    in_text_citation
)
from .config import DEFAULT_STYLE, STYLE_APA, STYLE_HARVARD, STYLE_IEEE

__version__ = "1.0.0"
__all__ = [
    "main",
    "load_cache",
    "save_cache",
    "lookup_single_work",
    "lookup_author_works",
    "reference_entry",
    "in_text_citation",
    "DEFAULT_STYLE",
    "STYLE_APA",
    "STYLE_HARVARD",
    "STYLE_IEEE"
]