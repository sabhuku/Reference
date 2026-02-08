# ZiReference Assistant

A Flask-based web application for managing academic references and citations with AI-assisted quality assurance.

## Overview

ZiReference Assistant is a production web application that helps students and researchers manage bibliographies, search academic databases, and ensure Harvard referencing compliance. It features multi-project support, AI-powered reference type classification, and automated style validation.

## Core Features

- **Multi-Project Bibliography Management**: Organize references across multiple projects with user authentication
- **Academic Search Integration**: Parallel search across CrossRef, PubMed, Google Books, Semantic Scholar, and arXiv
- **AI Reference Classification**: Machine learning pipeline for reference type detection (journal, book, website, etc.)
- **Harvard Style Compliance**: Automated validation against Harvard referencing standards
- **Citation Export**: Generate formatted citations in Harvard, APA, and IEEE styles
- **DOCX Import/Export**: Import existing bibliographies and export to Microsoft Word

## Production Deployment

### Entry Points

- **Production**: `wsgi.py` - WSGI entry point for production servers (Gunicorn, uWSGI, etc.)
- **Development**: `run_flask.py` - Flask development server with debug mode

### Quick Start (Development)

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Initialize database
python -m flask --app ui.app init-db

# Run development server
python run_flask.py
```

Access the application at `http://localhost:5000`

### Production Deployment

See [`DEPLOYMENT_CHECKLIST.md`](DEPLOYMENT_CHECKLIST.md) for comprehensive deployment guidance.

## Architecture

### Production Code

- **`src/`** - Core application logic
  - `reference_manager.py` - Main reference management and search orchestration
  - `api.py` - External API integrations (CrossRef, PubMed, Google Books, etc.)
  - `formatting.py` - Citation formatting (Harvard, APA, IEEE)
  - `normalizer.py` - Reference data normalization
  - `style/` - Harvard compliance validation subsystem
  - `ai_remediation/` - AI-assisted reference quality improvement
  - `importers/` - DOCX and other format importers

- **`ui/`** - Flask web application
  - `app.py` - Main Flask application and routes
  - `database.py` - SQLAlchemy models and database configuration
  - `forms.py` - WTForms for user input validation
  - `templates/` - Jinja2 HTML templates
  - `static/` - CSS, JavaScript, and assets

- **`modelling/`** - Machine learning pipeline
  - `pipeline.py` - Reference type classification (Stage 1)
  - `stage2_*.py` - Field extraction models (Stage 2)
  - `stage3_remediator.py` - AI-assisted remediation (Stage 3)
  - `*.pkl` - Trained model artifacts

- **`tests/`** - Comprehensive test suite
  - Unit tests, integration tests, and regression tests
  - Run with: `pytest tests/`

### Development Artifacts

- **`dev_archive/`** - Quarantined development tools (see [`dev_archive/README.md`](dev_archive/README.md))
  - Debug scripts, verification tools, legacy migrations
  - Not part of production deployment

- **`scripts/`** - Production utilities (see [`scripts/README.md`](scripts/README.md))
  - User creation, database maintenance

## Configuration

### Environment Variables

Create a `.env` file in the project root (see `.env.example`):

```bash
# Flask Configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=production  # or 'development'

# Database
DATABASE_URL=sqlite:///instance/references.db  # or PostgreSQL URL

# API Keys (Optional - improves search coverage)
GOOGLE_BOOKS_API_KEY=your-google-books-key
SEMANTIC_SCHOLAR_API_KEY=your-semantic-scholar-key

# Security
SESSION_COOKIE_SECURE=True  # Enable in production with HTTPS
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
```

### Database

The application uses SQLAlchemy with support for SQLite (development) and PostgreSQL (production).

**Initialize database:**
```bash
python -m flask --app ui.app init-db
```

## Security Considerations

### Authentication & Authorization

- User authentication via Flask-Login
- Password hashing with Werkzeug security
- Session-based authentication with secure cookies
- Per-user project isolation

### External Dependencies

- **CrossRef API**: No authentication required (rate-limited)
- **PubMed E-utilities**: No authentication required (3 req/sec limit)
- **Google Books API**: Optional API key (free tier available)
- **Semantic Scholar API**: No authentication required
- **arXiv API**: No authentication required

### Data Privacy

- User bibliographies stored in local database
- No user data sent to external APIs (only search queries)
- Cache stored locally (see `cache.json` - review for sensitive data)

### Known Security Notes

- **Cache file**: `cache.json` may contain API responses - review before sharing
- **Logs**: Application logs are excluded from version control (`.gitignore`)
- **API keys**: Store in `.env` file, never commit to version control

## API Integration

The application searches multiple academic databases in parallel:

1. **CrossRef** - 140M+ scholarly works (primary source)
2. **PubMed** - 35M+ biomedical citations
3. **Google Books** - Millions of books (requires API key)
4. **Semantic Scholar** - 200M+ papers (fallback)
5. **arXiv** - 2M+ preprints (fallback)

See [`SEARCH_SOURCES.md`](SEARCH_SOURCES.md) for detailed API documentation.

## AI/ML Pipeline

### Stage 1: Reference Type Classification
- Logistic Regression + TF-IDF
- Classifies references as journal, book, website, etc.
- Model: `modelling/stage1_reference_classifier_calibrated.pkl`

### Stage 2: Field Extraction
- Structured extraction of authors, title, year, journal, etc.
- Type-specific extractors for books, journals, websites
- Schema validation with confidence scoring

### Stage 3: AI Remediation (Optional)
- GPT-based assistance for incomplete references
- Confidence capping to prevent hallucination
- Never overwrites Stage 2 data

See [`modelling/PHASE_1_SUMMARY.md`](modelling/PHASE_1_SUMMARY.md) for ML architecture details.

## Documentation

### For Developers
- [`CHANGELOG.md`](CHANGELOG.md) - Version history and bug fixes
- [`ENHANCEMENT_SUMMARY.md`](ENHANCEMENT_SUMMARY.md) - Feature improvements
- [`SEARCH_SOURCES.md`](SEARCH_SOURCES.md) - API integration guide
- [`DICT_OBJECT_NORMALISATION.md`](DICT_OBJECT_NORMALISATION.md) - Data normalization layer

### For Operations
- [`DEPLOYMENT_CHECKLIST.md`](DEPLOYMENT_CHECKLIST.md) - Deployment procedures
- [`VERIFICATION_GUIDE.md`](VERIFICATION_GUIDE.md) - Manual testing guide
- [`RELEASE_NOTES.md`](RELEASE_NOTES.md) - Release documentation

### For QA/Testing
- [`TEST_RESULTS.md`](TEST_RESULTS.md) - Test execution results
- [`VERIFICATION_RESULTS.md`](VERIFICATION_RESULTS.md) - Verification outcomes

## Project Structure

```
referencing/
├── src/                    # Core application logic
├── ui/                     # Flask web application
├── modelling/              # ML models and training
├── tests/                  # Test suite
├── scripts/                # Production utilities
├── dev_archive/            # Development artifacts (not deployed)
├── instance/               # Database and runtime data
├── wsgi.py                 # Production entry point
├── run_flask.py            # Development entry point
├── requirements.txt        # Python dependencies
└── .env                    # Environment configuration (create from .env.example)
```

## Contributing

This is an academic project. For bug reports or feature requests, please contact the development team.

## License

Academic use only. See project documentation for details.

## Support

For deployment issues, see [`DEPLOYMENT_CHECKLIST.md`](DEPLOYMENT_CHECKLIST.md).  
For search configuration, see [`SEARCH_SOURCES.md`](SEARCH_SOURCES.md).  
For testing guidance, see [`VERIFICATION_GUIDE.md`](VERIFICATION_GUIDE.md).