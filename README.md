"""
Reference Assistant
==================

A tool for managing academic references and citations.

This module provides functionality to:
1. Search for academic works by title or author
2. Generate citations in multiple formats (Harvard, APA, IEEE)
3. Export formatted references to Word documents
4. Cache search results for faster access

Features:
- Multiple citation styles (Harvard, APA, IEEE)
- Integration with CrossRef and Google Books APIs
- Intelligent author name parsing
- Local caching of search results
- Export to Microsoft Word

Usage:
    from referencing import main
    main()

Configuration:
    See config.py for customizable settings

## Note about `input_validation.py` and import compatibility

`referencing.py` tries to import modern validation helper names (for example
`validate_menu_choice`, `validate_author_name`, `validate_search_query`). If
your workspace exposes older helper names instead (`get_valid_menu_choice`,
`get_user_confirmation`, `get_non_empty_input`), the script falls back to those
older names so the CLI and tests remain compatible. Keep one of these naming
conventions in `input_validation.py` or update the imports in `referencing.py`
after refactoring.
"""