from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify, Response
import json
import os
import io
import sys
import csv
import hashlib
from functools import wraps
from datetime import datetime, timedelta
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from io import StringIO
from werkzeug.utils import secure_filename
import portalocker

# Import Analytics Logger
from src.analytics import AnalyticsLogger

from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
import uuid

# Ensure project root (one level up) is on sys.path so top-level modules like
# `referencing.py` can be imported when running this script from the `ui/`
# folder.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Import the reference model (after path setup)
from src.referencing.models import Reference, Author
from src.models import Publication # Required for migration logic

# Import database models
from ui.database import db, User, Bibliography, Reference as DBReference, SavedComplianceReport
from src.utils.ref_normalizer import normalize_references  # Dict → Object adapter for SQL refs

from src.referencing import referencing
from ui.forms import ReferenceForm, LoginForm, RegistrationForm

# Persistence for manual refs
# Persistence for manual refs
# Using a data directory for session files
DATA_DIR = os.path.join(ROOT, 'data', 'sessions')
os.makedirs(DATA_DIR, exist_ok=True)

def get_session_id():
    """Get or create a constant session ID for anonymous data persistence."""
    if 'session_uuid' not in session:
        session['session_uuid'] = str(uuid.uuid4())
    return session['session_uuid']

def get_session_file_path():
    """Get the path to the current session's reference file."""
    sid = get_session_id()
    return os.path.join(DATA_DIR, f"{sid}.json")

def load_persisted_refs():
    """Load persisted references with file locking to prevent read corruption."""
    path = get_session_file_path()
    try:
        if os.path.exists(path):
            with portalocker.Lock(path, 'r', timeout=5, encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
    except portalocker.LockException:
        app.logger.error("Could not acquire lock to read references file (timeout)")
    except Exception as e:
        app.logger.error(f"Error loading persisted references: {e}")
    return []

def save_persisted_refs(refs):
    """Save persisted references with file locking to prevent write corruption."""
    path = get_session_file_path()
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        # Use portalocker for cross-platform file locking
        with portalocker.Lock(path, 'w', timeout=5, encoding='utf-8') as f:
            json.dump(refs, f, ensure_ascii=False, indent=2)
    except portalocker.LockException:
        app.logger.error("Could not acquire lock to save references file (timeout)")
        raise Exception("Unable to save references - file is locked by another process")
    except Exception as e:
        app.logger.error(f"Error saving persisted references: {e}")
        raise

def clear_persisted_refs():
    """Clear the persisted references file for the current session."""
    path = get_session_file_path()
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        app.logger.error(f"Error clearing persisted references: {e}")

import re

def normalize_authors(raw: str, return_metadata: bool = False):
    """
    Normalize a free-form authors string into a list of 'Surname, Given' entries.

    Heuristics supported:
    - Semicolon-separated or newline separated lists
    - 'and' separated lists
    - Comma-paired tokens like 'Smith, John, Doe, Jane' -> ['Smith, John', 'Doe, Jane']
    - Space-separated names 'John Smith, Mary Jones' -> ['Smith, John', 'Jones, Mary']
    - Single author in any form
    
    If return_metadata is True, returns a dict:
    {
        "authors": [...],
        "confidence": float (0.0-1.0),
        "ambiguous": bool,
        "parsing_method": str
    }
    """
    if not raw:
        return []
    
    # Simple split by semicolon or comma (if not part of Surname, Given)
    # This is a very basic fallback; a real implementation would use a proper parser
    if ';' in raw:
        authors = [a.strip() for a in raw.split(';')]
    else:
        # Try to detect if it's 'Surname, Given, Surname2, Given2' or 'Surname, Given; Surname2, Given2'
        parts = [a.strip() for a in raw.split(',')]
        if len(parts) > 1 and len(parts) % 2 == 0:
            # Pairs 
            authors = [f"{parts[i]}, {parts[i+1]}" for i in range(0, len(parts), 2)]
        else:
            authors = [raw.strip()]
            
    return authors

def save_compliance_report(result, project_id, filename=None):
    """Helper to persist a compliance report to the database."""
    if not project_id or not result:
        return None
        
    try:
        # Calculate source hash for deduplication
        # We hash the string representation of all references as a proxy for their content
        ref_keys = []
        for r in result.get('results', []):
            ref_keys.append(f"{r.get('display_title', '')}|{r.get('compliance_score', 0)}|{len(r.get('violations', []))}")
        
        combined_string = "|".join(ref_keys)
        source_hash = hashlib.sha256(combined_string.encode('utf-8')).hexdigest()
        
        # Check if an identical report exists for this project in the last hour
        # (to avoid spamming on refreshes)
        recent = SavedComplianceReport.query.filter_by(
            project_id=project_id,
            source_hash=source_hash
        ).order_by(SavedComplianceReport.created_at.desc()).first()
        
        if recent and (datetime.utcnow() - recent.created_at) < timedelta(hours=1):
            # Just update the timestamp
            recent.created_at = datetime.utcnow()
            db.session.commit()
            return recent.id
            
        # Create new record
        # Note: result['report'] is a ComplianceReport object
        report_obj = result.get('report')
        
        report = SavedComplianceReport(
            project_id=project_id,
            style=getattr(report_obj, 'style', 'Harvard'),
            filename=filename,
            overall_score=getattr(report_obj, 'overall_score', 0),
            error_count=report_obj.stats.error_count if hasattr(report_obj, 'stats') else 0,
            warning_count=report_obj.stats.warning_count if hasattr(report_obj, 'stats') else 0,
            info_count=report_obj.stats.info_count if hasattr(report_obj, 'stats') else 0,
            source_hash=source_hash,
            report_data=json.dumps(result, default=lambda x: x.__dict__ if hasattr(x, '__dict__') else str(x))
        )
        
        db.session.add(report)
        db.session.commit()
        return report.id
        
    except Exception as e:
        app.logger.error(f"Failed to save compliance report: {e}")
        db.session.rollback()
        return None

    if not raw:
        return {"authors": [], "confidence": 1.0, "ambiguous": False, "parsing_method": "empty"} if return_metadata else []
    
    s = raw.strip()
    
    # Heuristic: Detect and clean accidental Python list stringification
    # e.g., "['Author One', 'Author Two']" -> "Author One; Author Two"
    if s.startswith('[') and s.endswith(']'):
        try:
            # Safe literal eval is risky with untrusted input, so let's use regex-based cleaning
            # This handles ignoring the brackets and splitting by the quote-comma pattern
            inner = s[1:-1]
            if "'" in inner or '"' in inner:
                # remove quotes
                # Split by comma-space that is outside quotes... complex.
                # simpler: just strip brackets and quotes if it matches a pattern
                import ast
                try:
                    candidates = ast.literal_eval(s)
                    if isinstance(candidates, list):
                        parts = [str(c).strip() for c in candidates]
                        method = "list_repr_cleaned"
                        confidence = 0.95
                        return parts if not return_metadata else {
                            "authors": [fmt(p) for p in parts],
                            "confidence": confidence,
                            "ambiguous": False,
                            "parsing_method": method
                        }
                except:
                    pass
        except:
            pass
            
    parts = []
    method = "unknown"
    confidence = 0.0
    ambiguous = False
    
    # Split into candidate author strings
    if ';' in s:
        parts = [p.strip() for p in s.split(';') if p.strip()]
        method = "semicolon"
        confidence = 0.9
    elif '\n' in s:
        parts = [p.strip() for p in s.splitlines() if p.strip()]
        method = "newline"
        confidence = 0.9
    elif re.search(r'\band\b', s, flags=re.I):
        parts = [p.strip() for p in re.split(r'\band\b', s, flags=re.I) if p.strip()]
        method = "and_keyword"
        confidence = 0.9
    else:
        tokens = [t.strip() for t in s.split(',') if t.strip()]
        # Check for ambiguity: could this be comma-separated surnames?
        # If we interpret as "Surname, Given", we get N/2 authors.
        # If we interpret as "Surname", we get N authors.
        
        # if tokens look like pairs (surname, given, surname, given)
        if len(tokens) >= 2 and len(tokens) % 2 == 0:
            even_tokens_are_words = all(' ' not in tokens[i] for i in range(0, len(tokens), 2))
            
            # Ambiguity check: if even tokens *could* be full names (e.g. "Smith Jones"), it's ambiguous
            # But here we default to the pairing heuristic if it fits well.
            
            if even_tokens_are_words:
                parts = []
                for i in range(0, len(tokens), 2):
                    parts.append(tokens[i] + ', ' + tokens[i+1])
                method = "comma_pairs"
                confidence = 0.8
            else:
                # special-case: 'Surname Suffix, Given'
                combined = False
                if len(tokens) == 2:
                    last_token_of_first = tokens[0].split()[-1]
                    if last_token_of_first.rstrip('.') in {s.rstrip('.') for s in ("Jr", "Jr.", "Sr", "Sr.") }:
                        parts = [tokens[0] + ', ' + tokens[1]]
                        method = "comma_pair_suffix"
                        confidence = 0.85
                        combined = True
                
                if not combined:
                    if len(tokens) > 1 and all(' ' in t for t in tokens):
                        parts = tokens
                        method = "comma_separated_fullnames"
                        confidence = 0.6
                        # This is often ambiguous with comma pairs if names are simple
                    else:
                        parts = [p.strip() for p in s.split(',') if p.strip()]
                        method = "comma_fallback"
                        confidence = 0.4
                        ambiguous = True # Fallback is usually ambiguous
        else:
            # Odd number of tokens
            if len(tokens) > 1 and all(' ' in t for t in tokens):
                parts = tokens
                method = "comma_separated_fullnames"
                confidence = 0.6
            else:
                parts = [p.strip() for p in s.split(',') if p.strip()]
                method = "comma_fallback"
                confidence = 0.4
                if len(tokens) > 1:
                    ambiguous = True

    # common surname particles
    particles = {"van", "von", "de", "del", "da", "di", "la", "le", "du", "st", "st.", "der"}
    suffixes = {"Jr", "Jr.", "Sr", "Sr.", "II", "III", "IV"}

    def fmt(a: str) -> str:
        if ',' in a:
            family, given = [x.strip() for x in a.split(',', 1)]
            return f"{family}, {given}"
        parts = a.split()
        if len(parts) == 1:
            return parts[0]

        last = parts[-1]
        last_stripped = last.rstrip('.')
        suffix_stripped = {s.rstrip('.') for s in suffixes}
        is_initial_like = (
            (last.endswith('.') or len(last_stripped) <= 2)
            and last_stripped.isalpha()
            and last_stripped not in suffix_stripped
        )

        if is_initial_like and len(parts) >= 2:
            family = parts[0]
            given = ' '.join(parts[1:])
        else:
            if parts[-1] in suffixes and len(parts) >= 3:
                family = parts[-2] + ' ' + parts[-1]
                given = ' '.join(parts[:-2])
            else:
                if len(parts) >= 3:
                    i = len(parts) - 2
                    family_tokens = [parts[-1]]
                    while i >= 0 and parts[i].lower() in particles:
                        family_tokens.insert(0, parts[i])
                        i -= 1
                    if len(family_tokens) > 1:
                        family = ' '.join(family_tokens)
                        given = ' '.join(parts[:i+1]) if i >= 0 else ''
                    else:
                        family = parts[-1]
                        given = ' '.join(parts[:-1])
                else:
                    family = parts[-1]
                    given = ' '.join(parts[:-1])

        return f"{family}, {given}"

    formatted_authors = [fmt(p) for p in parts]
    
    if return_metadata:
        return {
            "authors": formatted_authors,
            "confidence": confidence,
            "ambiguous": ambiguous,
            "parsing_method": method
        }
    return formatted_authors

app = Flask(__name__)

# Validate required configuration
if not os.getenv("FLASK_SECRET"):
    raise RuntimeError(
        "FLASK_SECRET environment variable must be set. "
        "See .env.example for configuration template."
    )

# Configuration
app.config.update(
    SECRET_KEY=os.getenv("FLASK_SECRET"),
    RATELIMIT_DEFAULT="200 per day;50 per hour",
    RATELIMIT_HEADERS_ENABLED=True,
    SQLALCHEMY_DATABASE_URI=os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///references.db"),
    SQLALCHEMY_TRACK_MODIFICATIONS=False
)

# Initialize database
db.init_app(app)
migrate = Migrate(app, db)

# JSON Encoder for Dataclasses
from dataclasses import is_dataclass, asdict
from flask.json.provider import DefaultJSONProvider

class DataclassJSONProvider(DefaultJSONProvider):
    def default(self, o):
        if is_dataclass(o):
            return asdict(o)
        return super().default(o)

app.json = DataclassJSONProvider(app)

# Initialize login manager
login_manager = LoginManager(app)
login_manager.login_view =  'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[app.config["RATELIMIT_DEFAULT"]]
)

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429

@app.template_filter('in_text_citation')
def in_text_citation_filter(pub, style, index=None):
    """Jinja filter for in-text citations."""
    try:
        return referencing.in_text_citation(pub, style, index_number=index)
    except Exception:
        return "(UNKNOWN)"

@app.template_filter('reference_entry')
def reference_entry_filter(pub, style, index=None):
    """Jinja filter for bibliography entries."""
    try:
        return referencing.reference_entry(pub, style, index_number=index)
    except Exception as e:
        app.logger.error(f"Error formatting reference: {e} | Pub: {pub}")
        return f"Error formatting reference: {e}"

@app.errorhandler(400)
def bad_request_error(e):
    app.logger.error(f"Bad Request Error: {str(e)}")
    flash("Bad request. Please try again.", "error")
    return redirect(request.referrer or url_for("index"))

# Helpers
def get_session_refs():
    # If user is authenticated, return their project references
    if current_user.is_authenticated:
        from ui.database import Project, ProjectReference
        
        # Get current project ID
        project_id = session.get('current_project_id')
        
        # If no project selected, try to find default or any project
        if not project_id:
            project = Project.query.filter_by(
                user_id=current_user.id,
                id=f"{current_user.id}_default"
            ).first()
            if not project:
                project = Project.query.filter_by(user_id=current_user.id).first()
            if project:
                project_id = project.id
                session['current_project_id'] = project_id
        
        # Query references for the project
        if project_id:
            refs = ProjectReference.query.filter_by(project_id=project_id).all()
            # Normalize dicts → objects for attribute access (ref.title)
            return normalize_references([r.to_publication_dict() for r in refs])
            
        return []

    refs = session.get("refs")
    if refs is None:
        # Try to pre-populate from persisted refs on first access
        refs = load_persisted_refs()
        session["refs"] = refs
    return refs

from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, IntegerField, BooleanField
from wtforms.validators import DataRequired, Optional, NumberRange, Length, Regexp, ValidationError, URL
from datetime import datetime

class SearchForm(FlaskForm):
    # Basic search fields
    query = StringField('Query', validators=[DataRequired()], 
                       render_kw={"placeholder": "Enter search terms..."})
    stype = SelectField('Type', choices=[
        ('keywords', 'Keywords'),     # New default (general search)
        ('title', 'Title'),           # Strict title search
        ('author', 'Author'),
        ('doi', 'DOI')
    ], default='keywords')
    style = SelectField('Style', choices=[
        ('harvard', 'Harvard'), 
        ('apa', 'APA'), 
        ('ieee', 'IEEE'),
        ('mla', 'MLA'),
        ('chicago', 'Chicago'),
        ('vancouver', 'Vancouver')
    ])
    
    # Advanced search fields
    year_from = IntegerField('From', validators=[
        Optional(), 
        NumberRange(min=1900, max=datetime.now().year)
    ], render_kw={"placeholder": "Year from"})
    
    year_to = IntegerField('To', validators=[
        Optional(), 
        NumberRange(min=1900, max=datetime.now().year)
    ], render_kw={"placeholder": "Year to"})
    
    document_type = SelectField('Document Type', choices=[
        ('', 'All Types'),
        ('article', 'Journal Article'),
        ('book', 'Book'),
        ('conference', 'Conference Paper'),
        ('thesis', 'Thesis'),
        ('report', 'Report')
    ], default='')
    
    language = SelectField('Language', choices=[
        ('', 'Any Language'),
        ('en', 'English'),
        ('fr', 'French'),
        ('de', 'German'),
        ('es', 'Spanish'),
        ('zh', 'Chinese')
    ], default='')
    
    include_abstract = BooleanField('Include abstract in search', default=False)
    open_access = BooleanField('Open access only', default=False)
    
    submit = SubmitField('Search', render_kw={"class": "btn btn-primary"})
    reset = SubmitField('Reset', render_kw={"class": "btn btn-outline-secondary"})

# Initialize Reference Manager (Singleton for cache efficiency)
from src.reference_manager import ReferenceManager
ref_manager = ReferenceManager()

@app.route("/", methods=["GET", "POST"])
@login_required
@limiter.limit("10 per minute")  # Allow 10 requests per minute
@limiter.limit("200 per day")   # And 200 requests per day
def index():
    form = SearchForm()
    
    # Project-Scoped Retrieval for Home Page
    current_project_id = session.get('current_project_id')
    
    # DEBUG LOGGING
    app.logger.info(f"DEBUG: Index route accessed. Session Project ID: {current_project_id}")
    
    if current_user.is_authenticated:
        from ui.database import Project
        if not current_project_id:
            # For authenticated users, use SQL to find projects
            project = Project.query.filter_by(user_id=current_user.id).first()
            if project:
                current_project_id = project.id
                session['current_project_id'] = current_project_id
                app.logger.info(f"DEBUG: Defaulted to SQL project: {project.name} ({current_project_id})")
            else:
                # If no projects, the context processor or manage_projects will handle creation
                current_project_id = None
                app.logger.info("DEBUG: No SQL projects found for authenticated user")
    else:
        # Anonymous users use the JSON-based project manager
        if not current_project_id:
            projects = ref_manager.project_manager.list_projects()
            if projects:
                current_project_id = projects[0].id
                session['current_project_id'] = current_project_id
                app.logger.info(f"DEBUG: Defaulted to JSON project: {projects[0].name} ({current_project_id})")
            else:
                 current_project_id = "default"
                 app.logger.info("DEBUG: No JSON projects found, defaulting to 'default' ID")

    try:
        if current_user.is_authenticated:
            # SQL Source of Truth for Authenticated Users
            from ui.database import ProjectReference
            sql_refs = ProjectReference.query.filter_by(project_id=current_project_id).all()
            # Normalize dicts → objects immediately after SQL load
            refs = normalize_references([r.to_publication_dict() for r in sql_refs])
            app.logger.info(f"DEBUG: Loaded {len(refs)} refs from SQL for project {current_project_id}")
        else:
            # JSON Source of Truth for Anonymous Users
            refs = ref_manager.get_project_references(current_project_id)
            app.logger.info(f"DEBUG: Loaded {len(refs)} refs from JSON for project {current_project_id}")
        
        # MIGRATION: Consolidate legacy Bibliography/Reference data into the Project system
        if current_user.is_authenticated:
            migration_key = f'migration_complete_{current_user.id}'
            if not session.get(migration_key):
                try:
                    from ui.database import Bibliography, Reference, ProjectReference
                    legacy_bibs = Bibliography.query.filter_by(user_id=current_user.id).all()
                    migrated_count = 0
                    
                    # Get existing titles/DOIs in the current project to avoid duplicates during migration
                    existing_titles = {r.title.lower().strip() for r in refs if r.title}
                    existing_dois = {r.doi.lower().strip() for r in refs if r.doi}
                    
                    for bib in legacy_bibs:
                        for old_ref in bib.references:
                                # Safe attribute access for hybrid Ref types (Object/Dict)
                                if isinstance(old_ref, dict):
                                    title = old_ref.get('title', '').lower().strip()
                                    doi = old_ref.get('doi', '').lower().strip() if old_ref.get('doi') else None
                                    ref_source = old_ref.get('source')
                                    ref_pub_type = old_ref.get('pub_type')
                                    ref_authors = old_ref.get('authors')
                                    ref_year = old_ref.get('year')
                                    ref_journal = old_ref.get('journal')
                                    ref_publisher = old_ref.get('publisher')
                                    ref_location = old_ref.get('location')
                                    ref_volume = old_ref.get('volume')
                                    ref_issue = old_ref.get('issue')
                                    ref_pages = old_ref.get('pages')
                                else:
                                    title = (old_ref.title or '').lower().strip()
                                    doi = (old_ref.doi or '').lower().strip() if old_ref.doi else None
                                    ref_source = old_ref.source or ''
                                    ref_pub_type = old_ref.pub_type or ''
                                    ref_authors = old_ref.authors
                                    ref_year = old_ref.year or ''
                                    ref_journal = old_ref.journal or ''
                                    ref_publisher = old_ref.publisher or ''
                                    ref_location = old_ref.location or ''
                                    ref_volume = old_ref.volume or ''
                                    ref_issue = old_ref.issue or ''
                                    ref_pages = old_ref.pages or ''

                                if title not in existing_titles and (not doi or doi not in existing_dois):
                                    # Migrate to current project
                                    new_ref = ProjectReference(
                                        project_id=current_project_id,
                                        source=ref_source,
                                        pub_type=ref_pub_type,
                                        title=title, # Normalized title used for deduplication, original should be preserved?
                                        # Wait, we want the ORIGINAL title case for storage.
                                        # Let's fix that.
                                        authors=ref_authors,
                                        year=ref_year,
                                        journal=ref_journal,
                                        publisher=ref_publisher,
                                        location=ref_location,
                                        volume=ref_volume,
                                        issue=ref_issue,
                                        pages=ref_pages,
                                        doi=doi # Use normalized DOI if available
                                    )
                                    # Re-assign pure values if we normalized them too much above
                                    if isinstance(old_ref, dict):
                                        new_ref.title = old_ref.get('title', '')
                                        new_ref.doi = old_ref.get('doi', '')
                                    else:
                                        new_ref.title = old_ref.title
                                        new_ref.doi = old_ref.doi
                                    
                                    db.session.add(new_ref)
                                    migrated_count += 1
                                    existing_titles.add(title)
                                    if doi: existing_dois.add(doi)
                    
                    if migrated_count > 0:
                        db.session.commit()
                        app.logger.info(f"MIGRATION: Moved {migrated_count} references from legacy bibliographies to project {current_project_id}")
                        # Refresh refs list after migration from SQL
                        sql_refs = ProjectReference.query.filter_by(project_id=current_project_id).all()
                        refs = normalize_references([r.to_publication_dict() for r in sql_refs])
                    
                    # Mark migration complete (even if no refs to migrate)
                    session[migration_key] = True
                    
                except Exception as e:
                    db.session.rollback()
                    app.logger.error(f"Migration error: {e}")
                    # Do NOT mark migration complete on error

        # AUTO-MIGRATION: Check for legacy session refs if project is empty
        if not refs:
            legacy_refs = load_persisted_refs()
            if legacy_refs:
                 app.logger.info(f"MIGRATION: Found {len(legacy_refs)} legacy refs in session. Migrating to project '{current_project_id}'...")
                 try:
                     migrated_count = 0
                     for r_dict in legacy_refs:
                         # Convert dict to Publication object
                         # We use unpacking, assuming dict keys match Publication fields.
                         # Legacy dicts match the schema of Publication (from src.models)
                         try:
                             pub = Publication(**r_dict)
                             ref_manager.add_reference_to_project(pub, project_id=current_project_id)
                             migrated_count += 1
                         except Exception as e:
                             app.logger.error(f"Failed to migrate ref: {r_dict.get('title', 'Unknown')} - {e}")
                     
                     if migrated_count > 0:
                         ref_manager.save_projects()
                         clear_persisted_refs()
                         app.logger.info(f"MIGRATION: Successfully migrated {migrated_count} refs.")
                         # Reload refs from SQL
                         sql_refs = ProjectReference.query.filter_by(project_id=current_project_id).all()
                         refs = normalize_references([r.to_publication_dict() for r in sql_refs])
                         flash(f"Restored {migrated_count} references from previous session.", "success")
                 except Exception as e:
                     app.logger.error(f"Migration failed: {e}")

        if refs:
            app.logger.info(f"DEBUG: First ref type: {type(refs[0])}")
            app.logger.info(f"DEBUG: First ref data: {refs[0]}")
    except Exception as e:
        app.logger.error(f"Error loading project references: {e}")
        refs = []

    style = session.get("style", "harvard")
    
    # Handle form submission
    if form.validate_on_submit():
        try:
            query = form.query.data.strip()
            if not query:
                flash('Please enter a search term', 'error')
                return redirect(url_for('index'))
                
            search_type = form.stype.data
            style = form.style.data
            session["style"] = style  # Save the selected style
            
            # Extract filters dynamically (separation of concerns)
            # app.py matches routes to retrieval, but shouldn't know specific filter names
            filters = {}
            reserved_fields = {'query', 'stype', 'style', 'submit', 'reset', 'csrf_token'}
            
            for field in form:
                if field.name not in reserved_fields:
                    filters[field.name] = field.data

            # Log search parameters
            app.logger.info(
                f"Searching for '{query}' (type: {search_type}, filters: {filters})"
            )
            
            # No per-request cache loading needed use ref_manager
            results = []
            
            if search_type == "author":
                 # For author search, we only need the author name
                results = ref_manager.search_author_works(
                    query, 
                    **filters
                ) or []
                app.logger.info(f"Found {len(results)} results for author search")
            elif search_type == "doi":
                # Explicit DOI search
                res = ref_manager.search_single_work(query, use_parallel=False)
                results = [res] if res else []
                app.logger.info(f"Found {len(results)} results for DOI search")
            else:
                # For title or keyword search
                # Map UI search type to backend search mode
                # 'title' -> 'title' (strict), 'keywords' -> 'general' (broad)
                mode = 'title' if search_type == 'title' else 'general'
                
                results = ref_manager.search_works(
                    query, 
                    search_mode=mode,
                    **filters
                ) or []
                
                # Debug logging for troubleshooting UI 'View' button
                for r in results:
                    app.logger.info(f"UI DEBUG: '{r.title}' - URL: '{r.url}', DOI: '{r.doi}'")
                
                if results:
                    app.logger.info(f"Found {len(results)} results for {search_type} search")
                else:
                    app.logger.warning(f"No results found for query: {query}")
            
            # If it's an AJAX request, return JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True,
                    'results': results,
                    'count': len(results)
                })
            
            return render_template("results.html", 
                                query=query, 
                                results=results, 
                                search_type=search_type,
                                style=style,
                                form=form)  # Pass form back to template
                                
        except Exception as e:
            import sys
            import traceback
            sys.stderr.write(f"CRITICAL SEARCH ERROR: {e}\n")
            traceback.print_exc(file=sys.stderr)
            app.logger.error(f"Error during search: {str(e)}", exc_info=True)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
            flash('An error occurred while searching. Please try again.', 'error')
            return redirect(url_for('index'))
    
    # For GET requests or invalid form
    form.style.default = style
    form.process()  # Ensure the form is properly initialized
    
    # Recent Activity Logic (updated for project isolation & object/dict compatibility)
    # The index.html template expects FLAT objects (ref.title),
    # Calculate total counts from the SQL database (Source of Truth)
    if current_user.is_authenticated:
        from ui.database import ProjectReference
        if current_project_id:
            # Count references only for the CURRENT project
            count = ProjectReference.query.filter_by(project_id=current_project_id).count()
        else:
            count = 0
    else:
        # Session references for anonymous users
        count = len(get_session_refs())
    
    # Recent activity logic
    recent_refs = refs[-5:][::-1] if refs else []
    
    return render_template(
        "index.html", 
        form=form, 
        recent_refs=recent_refs, 
        total_refs=count,
        style=style
    )


    submit = SubmitField('Log In')

@app.route('/manual', methods=['GET'])
@login_required
def manual():
    """Render the manual entry form."""
    form = ReferenceForm()
    return render_template('manual.html', form=form)


@app.route('/manual_add', methods=['POST'])
@login_required
def manual_add():
    """Handle manual reference submission with validation."""
    form = ReferenceForm()
    
    # Validate form
    if not form.validate_on_submit():
        # Flash all validation errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field.replace('_', ' ').title()}: {error}", "error")
        return redirect(url_for('manual'))
    
    # Extract validated data
    title = form.title.data.strip()
    authors_raw = form.authors.data.strip() if form.authors.data else ''
    year = form.year.data.strip() if form.year.data else ''
    journal = form.journal.data.strip() if form.journal.data else ''
    publisher = form.publisher.data.strip() if form.publisher.data else ''
    volume = form.volume.data.strip() if form.volume.data else ''
    issue = form.issue.data.strip() if form.issue.data else ''
    pages = form.pages.data.strip() if form.pages.data else ''
    doi = form.doi.data.strip() if form.doi.data else ''
    url = form.url.data.strip() if form.url.data else ''
    access_date = form.access_date.data.strip() if form.access_date.data else ''
    pub_type = form.pub_type.data

    # Additional year range validation
    if year:
        try:
            year_int = int(year)
            if year_int < 1800 or year_int > 2100:
                flash('Year must be between 1800 and 2100', 'error')
                return redirect(url_for('manual'))
        except ValueError:
            flash('Year must be a valid number', 'error')
            return redirect(url_for('manual'))

    # Parse authors: accept a variety of common formats
    authors = normalize_authors(authors_raw) if authors_raw else []

    # Build reference object
    pub = {
        'source': 'manual',
        'pub_type': pub_type,
        'authors': authors,
        'year': year or 'n.d.',
        'title': title,
        'journal': journal,
        'publisher': publisher,
        'location': '',
        'volume': volume,
        'issue': issue,
        'pages': pages,
        'doi': doi,
        'url': url,
        'access_date': access_date,
    }

    # Validate against schema (hardening)
    from src.utils.input_validation import InputValidator
    validation_errors = InputValidator.validate_publication(pub)
    if validation_errors:
        for err in validation_errors:
            flash(err, 'error')
        return redirect(url_for('manual'))

    # Save reference
    try:
        refs = get_session_refs()
        
        # Early deduplication check
        if referencing.is_duplicate(pub, refs):
            flash('This reference is already in your session list.', 'info')
            return redirect(url_for('bibliography'))
        
        if current_user.is_authenticated:
            # Add to active project database
            from ui.database import Project, ProjectReference
            
            project_id = session.get('current_project_id')
            if not project_id:
                # Fallback: get or create default project
                project = Project.query.filter_by(user_id=current_user.id).first()
                if not project:
                    project = Project(
                        id=f"{current_user.id}_default",
                        user_id=current_user.id,
                        name="Default Project"
                    )
                    db.session.add(project)
                    db.session.commit()
                project_id = project.id
                session['current_project_id'] = project_id
            
            ref = ProjectReference.from_publication(pub, project_id)
            db.session.add(ref)
            db.session.commit()
        else:
            # Add to session
            refs.append(pub)
            session['refs'] = refs
            # Persist to disk with file locking
            save_persisted_refs(refs)
            
        flash('Manual reference added successfully', 'success')
    except Exception as e:
        app.logger.error(f"Error adding manual reference: {e}")
        flash('Error saving reference. Please try again.', 'error')
        return redirect(url_for('manual'))
    
    return redirect(url_for('bibliography'))


# Authentication Routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page."""
    if current_user.is_authenticated:
        return redirect(url_for('bibliography'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if user already exists
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered. Please log in or use a different email.', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already taken. Please choose a different username.', 'error')
            return redirect(url_for('register'))
        
        try:
            # Create new user
            user = User(
                email=form.email.data.lower().strip(),
                username=form.username.data.strip()
            )
            user.set_password(form.password.data)
            
            db.session.add(user)
            db.session.commit()
            
            # Create default bibliography for new user
            default_bib = Bibliography(
                user_id=user.id,
                name='My Bibliography',
                citation_style='APA'
            )
            db.session.add(default_bib)
            db.session.commit()
            
            # Migrate session refs if any
            session_refs = session.get('refs', [])
            if session_refs:
                # Get existing refs for the default bibliography to avoid duplicates
                existing_refs = [r.to_dict() for r in default_bib.references]
                
                added_count = 0
                for ref_dict in session_refs:
                    if not referencing.is_duplicate(ref_dict, existing_refs):
                        ref = DBReference.from_dict(ref_dict)
                        ref.bibliography_id = default_bib.id
                        db.session.add(ref)
                        existing_refs.append(ref_dict)  # Add to temporary list for next checks
                        added_count += 1
                db.session.commit()
                # Clear session refs after migration (cookie and disk)
                session.pop('refs', None)
                clear_persisted_refs()

                if added_count > 0:
                    app.logger.info(f"Imported {added_count} unique references for new user {user.username}")
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Registration error: {e}")
            flash('An error occurred during registration. Please try again.', 'error')
            return redirect(url_for('register'))
    
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page."""
    if current_user.is_authenticated:
        return redirect(url_for('bibliography'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Migrate session refs if any to the default project
            session_refs = session.get('refs', [])
            if session_refs:
                try:
                    from ui.database import Project, ProjectReference
                    # Find or create default project
                    project = Project.query.filter_by(
                        user_id=user.id,
                        name='Default Project'
                    ).first()
                    
                    if not project:
                        project = Project(
                            id=f"{user.id}_default",
                            user_id=user.id,
                            name='Default Project'
                        )
                        db.session.add(project)
                        db.session.commit()
                    
                    # Load existing references for deduplication
                    sql_refs = ProjectReference.query.filter_by(project_id=project.id).all()
                    existing_refs = normalize_references([r.to_publication_dict() for r in sql_refs])
                    
                    added_count = 0
                    for ref_dict in session_refs:
                        if not referencing.is_duplicate(ref_dict, existing_refs):
                            ref = ProjectReference.from_publication(ref_dict, project.id)
                            db.session.add(ref)
                            existing_refs.append(ref_dict)
                            added_count += 1
                    db.session.commit()
                    # Clear session refs after migration (cookie and disk)
                    session.pop('refs', None)
                    clear_persisted_refs()
                    
                    if added_count > 0:
                        flash(f'Imported {added_count} unique references from your session.', 'info')
                    else:
                        flash('All session references were already in your bibliography.', 'info')
                except Exception as e:
                    app.logger.error(f"Error migrating session refs: {e}")
            
            next_page = request.args.get('next')
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Invalid email or password. Please try again.', 'error')
    
    return render_template('login.html', form=form)


@app.route('/profile')
@login_required
def profile():
    """Display user profile and statistics."""
    # Count bibliographies and total references
    bib_count = len(current_user.bibliographies)
    total_refs = 0
    for bib in current_user.bibliographies:
        total_refs += len(bib.references)
        
    return render_template('profile.html', 
                         user=current_user,
                         bib_count=bib_count,
                         total_refs=total_refs)


@app.route('/logout')
@login_required
def logout():
    """Log out the current user."""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))


# Bibliography Management Routes
@app.route('/bibliographies')
@login_required
def bibliographies():
    """List all bibliographies for the current user."""
    user_bibs = Bibliography.query.filter_by(user_id=current_user.id).all()
    return render_template('bibliographies.html', bibliographies=user_bibs)


@app.route('/bibliographies/new', methods=['GET', 'POST'])
@login_required
def create_bibliography():
    """Create a new bibliography."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        style = request.form.get('style', 'APA')
        
        if not name:
            flash('Bibliography name is required', 'error')
            return redirect(url_for('create_bibliography'))
        
        try:
            bib = Bibliography(
                user_id=current_user.id,
                name=name,
                citation_style=style
            )
            db.session.add(bib)
            db.session.commit()
            flash(f'Bibliography "{name}" created successfully', 'success')
            return redirect(url_for('bibliographies'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error creating bibliography: {e}")
            flash('Error creating bibliography', 'error')
            return redirect(url_for('create_bibliography'))
    
    return render_template('bibliography_form.html', action='Create')


@app.route('/bibliographies/<int:bib_id>')
@login_required
def view_bibliography(bib_id):
    """View a specific bibliography."""
    bib = Bibliography.query.get_or_404(bib_id)
    
    # Security: ensure user owns this bibliography
    if bib.user_id != current_user.id:
        flash('You do not have permission to view this bibliography', 'error')
        return redirect(url_for('bibliographies'))
    
    refs = DBReference.query.filter_by(bibliography_id=bib_id).all()
    ref_dicts = [ref.to_dict() for ref in refs]
    
    return render_template('bibliography_view.html', bibliography=bib, refs=ref_dicts)


@app.route('/bibliographies/<int:bib_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_bibliography(bib_id):
    """Edit/rename a bibliography."""
    bib = Bibliography.query.get_or_404(bib_id)
    
    # Security check
    if bib.user_id != current_user.id:
        flash('You do not have permission to edit this bibliography', 'error')
        return redirect(url_for('bibliographies'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        style = request.form.get('style', bib.citation_style)
        
        if not name:
            flash('Bibliography name is required', 'error')
            return redirect(url_for('edit_bibliography', bib_id=bib_id))
        
        try:
            bib.name = name
            bib.citation_style = style
            db.session.commit()
            flash(f'Bibliography updated successfully', 'success')
            return redirect(url_for('bibliographies'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating bibliography: {e}")
            flash('Error updating bibliography', 'error')
    
    return render_template('bibliography_form.html', action='Edit', bibliography=bib)


@app.route('/bibliographies/<int:bib_id>/delete', methods=['POST'])
@login_required
def delete_bibliography(bib_id):
    """Delete a bibliography and all its references."""
    bib = Bibliography.query.get_or_404(bib_id)
    
    # Security check
    if bib.user_id != current_user.id:
        flash('You do not have permission to delete this bibliography', 'error')
        return redirect(url_for('bibliographies'))
    
    try:
        bib_name = bib.name
        db.session.delete(bib)  # Cascade will delete all references
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting bibliography: {e}")
        flash('Error deleting bibliography', 'error')
    
    return redirect(url_for('bibliographies'))


@app.route('/api/references/<int:ref_id>/remediate', methods=['POST'])
@login_required
def remediate_reference(ref_id):
    """Handle remediation actions (accept/reject) for a reference."""
    ref = ProjectReference.query.get_or_404(ref_id)
    
    # Security: Ensure user owns the project this reference belongs to
    # (Assuming project ownership check via project query or relationship)
    # Simple check:
    project = Project.query.get(ref.project_id)
    if not project or project.user_id != current_user.id:
         return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    data = request.get_json()
    action = data.get('action')
    
    if not ref.remediation:
        return jsonify({'success': False, 'error': 'No remediation data found'}), 400

    try:
        if action == 'accept':
            suggestions = ref.remediation.get('suggested_fields', {})
            # Update fields
            for field, candidates in suggestions.items():
                if candidates:
                    val = candidates[0].get('value')
                    if hasattr(ref, field):
                        if field == 'authors':
                             # Special handling for authors list -> JSON storage
                             # Only update if val is a list; otherwise wrap it?
                             # Stage 3 usually returns a list of strings for authors.
                             ref.authors = json.dumps(val) if isinstance(val, list) else json.dumps([str(val)])
                             # Note: ref.authors is stored as JSON string in DB
                        else:
                             setattr(ref, field, val)
            
            # Update remediation status
            rem_data = dict(ref.remediation) # Copy to mutate
            rem_data['requires_review'] = False
            rem_data['status'] = 'accepted'
            rem_data['resolved_at'] = datetime.utcnow().isoformat()
            ref.remediation = rem_data
            
            db.session.commit()
            return jsonify({'success': True, 'message': 'Suggestions accepted'})
            
        elif action == 'reject':
            # Update remediation status
            rem_data = dict(ref.remediation)
            rem_data['requires_review'] = False
            rem_data['status'] = 'rejected'
            rem_data['resolved_at'] = datetime.utcnow().isoformat()
            ref.remediation = rem_data
            
            db.session.commit()
            return jsonify({'success': True, 'message': 'Suggestions dismissed'})
            
        else:
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
            
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Remediation error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
        flash(f'Bibliography "{bib_name}" deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting bibliography: {e}")
        flash('Error deleting bibliography', 'error')
    
    return redirect(url_for('bibliographies'))


@app.route('/remove/<int:idx>', methods=['GET', 'POST'])
@login_required
def remove(idx):
    refs = get_session_refs()
    if 0 <= idx < len(refs):
        if current_user.is_authenticated:
            # Authenticated: Delete from DB
            from ui.database import ProjectReference
            ref_data = refs[idx]
            ref_id = ref_data.get('id')
            if ref_id:
                ref = ProjectReference.query.get(ref_id)
                if ref and ref.project.user_id == current_user.id:
                    db.session.delete(ref)
                    db.session.commit()
                    flash('Reference deleted permanently.')
                else:
                    flash('Reference not found or permission denied.', 'error')
            else:
                 flash('Invalid reference ID.', 'error')
        else:
            # Anonymous: Delete from session
            refs.pop(idx)
            session['refs'] = refs
            save_persisted_refs(refs)
            flash('Removed item')
    else:
        flash('Invalid index', 'error')
    return redirect(url_for('bibliography'))


@app.route('/edit/<int:idx>', methods=['GET', 'POST'])
@login_required
def edit(idx):
    refs = get_session_refs()
    if request.method == 'GET':
        if 0 <= idx < len(refs):
            pub = refs[idx]
            # Pre-fill form with existing data
            # Ensure authors are formatted as a string, not a Python list repr
            form_data = pub.copy()
            if isinstance(form_data.get('authors'), list):
                form_data['authors'] = '; '.join(form_data['authors'])
                
            form = ReferenceForm(data=form_data)
            return render_template('manual.html', edit=True, idx=idx, pub=pub, form=form)
        flash('Invalid index')
        return redirect(url_for('bibliography'))

    # POST: update
    if 0 <= idx < len(refs):
        form = ReferenceForm()
        if not form.validate_on_submit():
            # Flash all validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"{field.replace('_', ' ').title()}: {error}", "error")
            return redirect(url_for('edit', idx=idx))

        title = form.title.data.strip()
        authors_raw = form.authors.data.strip() if form.authors.data else ''
        year = form.year.data.strip() if form.year.data else ''
        journal = form.journal.data.strip() if form.journal.data else ''
        publisher = form.publisher.data.strip() if form.publisher.data else ''
        volume = form.volume.data.strip() if form.volume.data else ''
        issue = form.issue.data.strip() if form.issue.data else ''
        pages = form.pages.data.strip() if form.pages.data else ''
        doi = form.doi.data.strip() if form.doi.data else ''
        url = form.url.data.strip() if form.url.data else ''
        pub_type = form.pub_type.data

        authors = normalize_authors(authors_raw)
        
        # New data dict
        pub_data = {
            'source': 'manual',
            'pub_type': pub_type,
            'authors': authors or [],
            'year': year or 'n.d.',
            'title': title,
            'journal': journal,
            'publisher': publisher,
            'volume': volume,
            'issue': issue,
            'pages': pages,
            'doi': doi,
            'url': url,
        }
        
        if current_user.is_authenticated:
            # Authenticated: Update DB
            from ui.database import ProjectReference
            ref_dict = refs[idx]
            ref_id = ref_dict.get('id')
            if ref_id:
                ref = ProjectReference.query.get(ref_id)
                if ref and ref.project.user_id == current_user.id:
                    # Update fields
                    ref.title = title
                    ref.authors = json.dumps(authors)
                    ref.year = year or 'n.d.'
                    ref.journal = journal
                    ref.publisher = publisher
                    ref.volume = volume
                    ref.issue = issue
                    ref.pages = pages
                    ref.doi = doi
                    ref.url = url
                    ref.pub_type = pub_type
                    
                    db.session.commit()
                    
                    # Log edit
                    try:
                         AnalyticsLogger.log_edit_event(str(ref_id), {"old": ref_dict, "new": pub_data}, project_id=session.get('current_project_id'))
                    except Exception as e:
                        app.logger.warning(f"Analytics logging failed: {e}")
                        
                    flash('Reference updated in database.')
                else:
                    flash('Reference not found or permission denied.', 'error')
            else:
                 flash('Invalid reference ID.', 'error')
        else:
            # Anonymous: Update session
            # Capture old state for analytics
            old_ref = refs[idx].copy()
            refs[idx] = pub_data
            session['refs'] = refs
            save_persisted_refs(refs)
            
            # Log edit
            try:
                AnalyticsLogger.log_edit_event(str(idx), {"old": old_ref, "new": pub_data}, project_id=session.get('current_project_id'))
            except Exception as e:
                app.logger.warning(f"Analytics logging failed: {e}")
                
            flash('Reference updated')
            
    else:
        flash('Invalid index')
    return redirect(url_for('bibliography'))

@app.route("/search", methods=["POST"])
@login_required
@limiter.limit("5 per minute")  # Stricter limit on search
@limiter.limit("50 per day")   # And 50 per day
def search():
    q = request.form.get("query", "").strip()
    search_type = request.form.get("stype", "title")
    # capture selected style and persist in session
    style = request.form.get("style") or session.get("style", "harvard")
    session["style"] = style
    if not q:
        flash("Please enter a query.")
        return redirect(url_for("index"))

    cache = referencing.load_cache()
    results = []
    if search_type == "author":
        results = referencing.lookup_author_works(q, cache)
    else:
        m = referencing.lookup_single_work(q, cache)
        if m:
            results = [m]

    # normalize results for template
    return render_template(
        "results.html", 
        query=q, 
        results=results, 
        search_type=search_type
    )
@app.route('/export/<format>')
@login_required
@limiter.limit("10 per minute")
def export(format):
    """Export references in the specified format."""
    idx = request.args.get('idx', None)
    if idx is not None:
        # Export single reference
        try:
            idx = int(idx)
            refs = get_session_refs()
            if 0 <= idx < len(refs):
                refs = [refs[idx]]
            else:
                return "Invalid reference index", 400
        except (ValueError, IndexError):
            return "Invalid reference index", 400
    else:
        # Export all references
        refs = get_session_refs()
        
    if not refs:
        return "No references to export", 400
        
    try:
        if format == 'bibtex':
            return Response(
                referencing.export_bibtex(refs),
                mimetype='text/plain',
                headers={'Content-Disposition': f'attachment;filename=reference_{idx}.bib' if idx is not None else 'references.bib'}
            )
        elif format == 'ris':
            return Response(
                referencing.export_ris(refs),
                mimetype='text/plain',
                headers={'Content-Disposition': f'attachment;filename=reference_{idx}.ris' if idx is not None else 'references.ris'}
            )
        elif format == 'json':
            return jsonify(refs[0] if idx is not None else [r for r in refs])
        elif format == 'csv':
            output = StringIO()
            writer = csv.writer(output)
            # Write header
            writer.writerow(['Title', 'Authors', 'Year', 'Journal', 'Volume', 'Issue', 'Pages', 'DOI', 'URL'])
            # Write data
            for r in refs:
                writer.writerow([
                    r.get('title', ''),
                    '; '.join(r.get('authors', [])) if isinstance(r.get('authors'), list) else r.get('authors', ''),
                    r.get('year', ''),
                    r.get('journal', ''),
                    r.get('volume', ''),
                    r.get('issue', ''),
                    r.get('pages', ''),
                    r.get('doi', ''),
                    r.get('url', '')
                ])
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment;filename=reference_{idx}.csv' if idx is not None else 'references.csv'}
            )
        else:
            return f"Unsupported format: {format}", 400
            
    except Exception as e:
        app.logger.error(f"Export error: {str(e)}")
        return f"Error exporting references: {str(e)}", 500

@app.route("/add", methods=["POST"])
@login_required
@limiter.limit("5 per minute")  # Stricter limit on reference addition
@limiter.limit("50 per day")   # And 50 per day
def add():
    app.logger.info(f"Add route called. Form data: {request.form.keys()}")
        
    # expects a JSON payload of the publication dict
    data = request.form.get("pub")
    if not data:
        flash("No publication data received", "error")
        return redirect(request.referrer or url_for("index"))
        
    try:
        pub = json.loads(data)
        
        # Schema Validation
        is_valid, error_msg = referencing.validate_publication(pub)
        if not is_valid:
            app.logger.warning(f"Invalid publication data: {error_msg}")
            flash(f"Invalid reference data: {error_msg}", "error")
            return redirect(request.referrer or url_for("index"))

        # Enrichment (fix truncation)
        try:
             # Convert dict to internal Publication model for enrichment
             # Note: pub['authors'] is a list of strings here
             from src.models import Publication as InternalPub
             
             p_obj = InternalPub(
                 source=pub.get('source', 'unknown'),
                 pub_type=pub.get('pub_type', 'article'),
                 authors=pub.get('authors', []),
                 year=pub.get('year', 'n.d.'),
                 title=pub.get('title', ''),
                 journal=pub.get('journal', ''),
                 publisher=pub.get('publisher', ''),
                 location=pub.get('location', ''),
                 volume=pub.get('volume', ''),
                 issue=pub.get('issue', ''),
                 pages=pub.get('pages', ''),
                 doi=pub.get('doi', ''),
                 match_type=pub.get('match_type', 'manual'),
                 confidence_score=pub.get('confidence_score', 1.0),
                 retrieval_method=pub.get('retrieval_method', 'manual')
             )
             
             # Enrich
             max_retries = 1 # Don't retry inside a request handler
             p_enriched = ref_manager.enrich_publication(p_obj)
             
             # Update pub dict with enriched data
             pub['title'] = p_enriched.title
             pub['authors'] = p_enriched.authors
             pub['year'] = p_enriched.year
             pub['journal'] = p_enriched.journal
             pub['publisher'] = p_enriched.publisher
             pub['volume'] = p_enriched.volume
             pub['issue'] = p_enriched.issue
             pub['pages'] = p_enriched.pages
             pub['doi'] = p_enriched.doi
             # Keep original source if desired, or update?
             # For now, trust the enrichment flow's decision
             
        except Exception as e:
             app.logger.warning(f"Enrichment failed (continuing with original data): {e}")

    except Exception as e:
        app.logger.error(f"Error parsing publication data: {str(e)}")
        flash("Invalid publication data format", "error")
        return redirect(request.referrer or url_for("index"))

    try:
        refs = get_session_refs()
        
        # Early deduplication check
        if referencing.is_duplicate(pub, refs):
            flash('This reference is already in your bibliography.', 'info')
            return redirect(request.referrer or url_for("index"))
            
        if current_user.is_authenticated:
            # Add to active project
            from ui.database import Project, ProjectReference
            
            project_id = session.get('current_project_id')
            if not project_id:
                # Fallback: find default project or create it
                project = Project.query.filter_by(
                    user_id=current_user.id, 
                    id=f"{current_user.id}_default"
                ).first()
                
                if not project:
                     # Create default if absolutely missing (safety net)
                    try:
                        project = Project(
                            id=f"{current_user.id}_default",
                            user_id=current_user.id,
                            name="Default Project"
                        )
                        db.session.add(project)
                        db.session.commit()
                    except:
                        db.session.rollback()
                        # Verify if it was racing
                        project = Project.query.filter_by(user_id=current_user.id).first()
                
                if project:
                    project_id = project.id
                    session['current_project_id'] = project_id
            
            if project_id:
                ref = ProjectReference.from_publication(pub, project_id)
                db.session.add(ref)
                db.session.commit()
                app.logger.info(f"SUCCESS: Added reference to project {project_id}")
            else:
                 app.logger.error("Could not determine project for authenticated user")
                 flash("Error: No active project found", "error")
                 return redirect(request.referrer or url_for("index"))
        else:
            # Add to session
            refs.append(pub)
            session["refs"] = refs
            # persist
            save_persisted_refs(refs)
            
        flash('Added to bibliography', 'success')
    except Exception as e:
        app.logger.error(f"Error adding reference: {str(e)}")
        flash("An error occurred while adding the reference", "error")
        
    return redirect(request.referrer or url_for("index"))


@app.route('/cite', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
@limiter.limit("100 per day")
def cite():
    """
    Generate in-text citation and full reference for a single publication.

    Expects form fields:
      - pub: JSON of the publication
      - style: citation style ('harvard', 'apa', 'ieee') optional
    """
    app.logger.info(f"Cite route called. Form data: {request.form.keys()}")
            
    pub_data = request.form.get("pub")
    style = request.form.get("style", "harvard")

    if not pub_data:
        flash("No publication data provided", "error")
        return redirect(request.referrer or url_for("index"))

    try:
        pub = json.loads(pub_data)
        
        # Schema Validation
        is_valid, error_msg = referencing.validate_publication(pub)
        if not is_valid:
            flash(f"Invalid reference data: {error_msg}", "error")
            return redirect(request.referrer or url_for("index"))
            
    except json.JSONDecodeError as e:
        app.logger.error(f"Error parsing publication data: {str(e)}")
        flash("Invalid publication data format", "error")
        return redirect(request.referrer or url_for("index"))

    try:
        # Generate the citation
        citation = referencing.in_text_citation(pub, style)
        full_ref = referencing.reference_entry(pub, style)
        
        # Flash the citation to the user
        flash(f"In-text citation ({style.upper()}): {citation}", "success")
        flash(f"Full reference: {full_ref}", "info")
        
        return redirect(request.referrer or url_for("index"))
        
    except Exception as e:
        app.logger.error(f"Error in cite for pub '{pub.get('title', 'Unknown')}': {str(e)}", exc_info=True)
        flash(f"Could not generate citation for '{pub.get('title', 'this reference')}'. It may be missing required fields.", "error")
        return redirect(request.referrer or url_for("index"))

@app.route("/compliance")
@login_required
def check_compliance():
    """Run Harvard compliance check on current bibliography."""
    refs_data = get_session_refs()
    
    # Deduplicate to match bibliography view
    # The bibliography page hides duplicates, so the report should too.
    refs_data = referencing.dedupe(refs_data)
    
    # Convert dicts back to Publication objects for checking
    # Note: ref_manager expects Publication objects, but get_session_refs returns dicts
    from src.models import Publication
    
    publications = []
    for r in refs_data:
        # Robust conversion
        try:
            # Handle potential mismatch in fields if raw dict
            # Minimal reqs: authors, year, title
            authors = r.get('authors', [])
            if isinstance(authors, str): authors = [authors]
            
            pub = Publication(
                source=r.get('source', 'manual'),
                pub_type=r.get('pub_type', 'unknown'),
                authors=authors,
                year=str(r.get('year', '')),
                title=r.get('title', ''),
                journal=r.get('journal', ''),
                publisher=r.get('publisher', ''),
                location=r.get('location', ''),
                volume=str(r.get('volume', '')),
                issue=str(r.get('issue', '')),
                pages=str(r.get('pages', '')),
                doi=r.get('doi', '')
            )
            publications.append(pub)
        except Exception as e:
            app.logger.warning(f"Skipping malformed ref for check: {e}")
            
    if not publications:
        flash("No references to check.", "info")
        return redirect(url_for('bibliography'))

    # Run check
    try:
        origin = request.args.get('origin', 'bibliography')
        result = ref_manager.check_style_compliance(publications)
        
        # Log analytics
        project_id = session.get('current_project_id')
        AnalyticsLogger.log_compliance_report(result, project_id=project_id)
        
        # PERSISTENCE: Save report if in a project
        if project_id:
            save_compliance_report(result, project_id)
        
        return render_template("compliance_report.html", result=result, origin=origin)
    except Exception as e:
        app.logger.error(f"Compliance check failed: {e}")
        flash("Error running compliance check.", "error")
        return redirect(url_for('bibliography'))

@app.route("/bibliography", methods=["GET"])
@app.route("/bibliography")
@login_required
@limiter.limit("10 per minute")  # Allow 10 requests per minute
@limiter.limit("200 per day")   # And 200 requests per day
def bibliography():
    refs = get_session_refs()
    style = request.args.get("style", session.get("style", "harvard"))
    session["style"] = style
    sort_by = request.args.get("sort", "author")
    sort_dir = request.args.get("dir", "asc")
    
    # Wrap refs to preserve original indices
    wrapped_refs = [{'data': r, 'original_index': i} for i, r in enumerate(refs)]
    
    def sort_key(w):
        d = w['data']
        if sort_by == 'recent':
            # Sort by added_at (descending) or index (descending) if no date
            ts = d.get('added_at')
            if ts:
                return ts
            return w['original_index']
            
        elif sort_by == 'year':
            return (d.get('year', ''), d.get('title', ''))
            
        elif sort_by == 'title':
            return (d.get('title', ''), d.get('year', ''))
            
        else: # author (default)
            authors = d.get('authors', [])
            author_str = authors[0] if authors and isinstance(authors, list) else str(authors)
            return (author_str, d.get('year', ''), d.get('title', ''))

    # Apply sort
    # 'recent' defaults to descending conventionally, but we respect sort_dir if provided
    # However, if it's the first visit to 'recent', we might want desc.
    # For simplicity, we just use sort_dir logic for all.
    reverse_sort = (sort_dir == 'desc')
    
    # Special case: 'recent' ascending is oldest first, descending is newest first.
    # Since sort_key returns timestamp/index, asc (default) is oldest first.
    # So reverse_sort = True (desc) is newest first.
    # This aligns perfectly.
    
    wrapped_refs.sort(key=sort_key, reverse=reverse_sort)
    
    refs_sorted = wrapped_refs

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 10
    total_refs = len(refs_sorted)
    total_pages = (total_refs + per_page - 1) // per_page if total_refs > 0 else 1
    
    # Slice references
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_refs = refs_sorted[start_idx:end_idx]
    
    return render_template("bibliography.html", 
                         refs=paginated_refs, 
                         style=style,
                         sort_by=sort_by,
                         sort_dir=sort_dir,
                         page=page,
                         total_pages=total_pages,
                         total_refs=total_refs)

@app.route("/export_word", methods=["GET"])
@login_required
@limiter.limit("10 per hour")  # Limit exports to prevent abuse
def export_word():
    idx = request.args.get('idx', None)
    if idx is not None:
        # Export single reference
        try:
            idx = int(idx)
            refs = get_session_refs()
            if 0 <= idx < len(refs):
                refs = [refs[idx]]
            else:
                return "Invalid reference index", 400
        except (ValueError, IndexError):
            return "Invalid reference index", 400
    else:
        # Export all references
        refs = get_session_refs()
    style = session.get("style", "harvard")
    uniq = referencing.dedupe(refs)
    refs_sorted = referencing.sort_for_bibliography(uniq, style)
    
    # Validate download folder and filename for security
    try:
        download_folder = os.path.abspath(referencing.DOWNLOAD_FOLDER)
        safe_filename = secure_filename(referencing.WORD_FILENAME)
        
        path = referencing.save_references_to_word(
            refs_sorted, download_folder, safe_filename, set(), style
        )
        
        # Verify the final path is within the allowed directory
        abs_path = os.path.abspath(path)
        if not abs_path.startswith(download_folder):
            app.logger.error(f"Path traversal attempt blocked: {path}")
            flash("Invalid file path", "error")
            return redirect(url_for("bibliography"))
        
        return send_file(abs_path, as_attachment=True)
    except Exception as e:
        return redirect(url_for("bibliography"))

@app.route("/api/cite")
@login_required
@limiter.limit("60 per minute")
def api_cite():
    """Return formatted citations for a reference in multiple styles."""
    try:
        idx = request.args.get('idx', type=int)
        if idx is None:
            return jsonify({'error': 'Missing index'}), 400
            
        refs = get_session_refs()
        if idx < 0 or idx >= len(refs):
            return jsonify({'error': 'Reference not found'}), 404
            
        ref = refs[idx]
        
        # We need to use the formatter logic. 
        from src.formatting import CitationFormatter
        
        styles = ['harvard', 'apa', 'mla', 'chicago', 'ieee', 'vancouver']
        citations = {}
        
        for s in styles:
            citations[s] = CitationFormatter.format_reference(ref, s)
            
        return jsonify({
            'success': True,
            'title': ref.get('title', 'Unknown Title'),
            'citations': citations
        })
    except Exception as e:
        app.logger.error(f"Error generating citations: {e}")
        return jsonify({'error': str(e)}), 500

@app.route("/import", methods=["GET", "POST"])
@login_required
def import_file():
    """Handle file upload and run compliance check."""
    if request.method == "POST":
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
            
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
            
        if file:
            try:
                # Secure filename
                filename = secure_filename(file.filename)
                
                # Check extension roughly
                ext = filename.lower().split('.')[-1]
                if ext not in ['json', 'ris', 'txt', 'docx', 'doc']:
                    flash('Unsupported file extension. Please use JSON, RIS, TXT, or DOCX.', 'error')
                    return redirect(request.url)
                
                # Read content
                if ext in ['docx', 'doc']:
                    content = file.read()
                else:
                    content = file.read().decode('utf-8', errors='replace')
                
                # Get importer
                from src.importers import get_importer_for_file
                importer = get_importer_for_file(filename)
                
                # Parse
                imported_pubs = importer.parse(content)
                
                if not imported_pubs:
                    flash('No references found in file or invalid format.', 'error')
                    return redirect(request.url)
                    
                # Deduplicate? YES, to remove exact duplicates within the file
                imported_pubs = referencing.dedupe(imported_pubs)
                
                # Run Compliance Check immediately
                result = ref_manager.check_style_compliance(imported_pubs)
                
                # Tag result as import for UI context?
                # PERSISTENCE: Save report
                project_id = session.get('current_project_id')
                save_compliance_report(result, project_id, filename=filename)
                
                flash(f"Successfully imported and checked {len(imported_pubs)} references.", "success")
                return render_template("compliance_report.html", result=result, origin='index')
                
            except Exception as e:
                app.logger.error(f"Import error: {e}")
                flash('An error occurred during import.', 'error')
                return redirect(request.url)

    return render_template("import.html")

@app.route("/analytics", methods=["GET"])
@login_required
@limiter.limit("20 per minute")
def analytics_dashboard():
    """Display the visual analytics dashboard."""
    try:
        project_id = session.get('current_project_id')
        stats = AnalyticsLogger.get_summary_stats(project_id=project_id)
        suggestions = AnalyticsLogger.get_proactive_suggestions(project_id=project_id)
        return render_template("analytics.html", stats=stats, suggestions=suggestions)
    except Exception as e:
        app.logger.error(f"Analytics dashboard error: {e}")
        flash("Error loading analytics data.", "error")
        return redirect(url_for('index'))

# ============================================================================
# PIPELINE ANALYSIS ROUTE (ML Pipeline Results View)
# ============================================================================

@app.route('/pipeline/analyze', methods=['GET', 'POST'])
@login_required
@limiter.limit("5 per minute")
def pipeline_analyze():
    """
    Pipeline analysis route - displays ML pipeline results in read-only view.
    
    SAFETY: Runs pipeline in analysis_mode=True to prevent Stage 3 execution.
    """
    from datetime import datetime
    
    if request.method == 'GET':
        # Display input form
        return render_template('pipeline_analyze_form.html')
    
    # POST: Process reference
    reference_text = request.form.get('reference_text', '').strip()
    
    if not reference_text:
        flash('Please enter a reference to analyze.', 'warning')
        return redirect(url_for('pipeline_analyze'))
    
    try:
        # Import pipeline
        from modelling.pipeline import run_pipeline
        
        # Run pipeline in ANALYSIS MODE (Stage 3 disabled)
        result = run_pipeline(reference_text, analysis_mode=True)
        
        # Add timestamp for immutability
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Log analytics (backend-only)
        from src.analytics import AnalyticsLogger
        current_project_id = session.get('current_project_id')
        AnalyticsLogger.log_pipeline_analysis(result, project_id=current_project_id)
        
        return render_template('pipeline_result.html', 
                             result=result, 
                             timestamp=timestamp)
    
    except Exception as e:
        app.logger.error(f"Pipeline analysis error: {e}")
        flash(f'Pipeline analysis failed: {str(e)}', 'danger')
        return redirect(url_for('pipeline_analyze'))

# Simple health route
@app.route("/health", methods=["GET"])
def health():
    return "ok", 200


# ============================================================================
# PROJECT MANAGEMENT ROUTES (Multi-Project UI Feature)
# ============================================================================

@app.route('/projects')
@login_required
def manage_projects():
    """Project management page for authenticated users."""
    from ui.database import Project, ProjectReference
    
    # Get all projects for current user
    projects = Project.query.filter_by(user_id=current_user.id).all()
    
    # Convert to dictionaries with stats
    project_list = [p.to_dict() for p in projects]
    
    return render_template('projects.html', projects=project_list)


@app.route('/projects/create', methods=['POST'])
@login_required
def create_project():
    """Create a new project for the authenticated user."""
    from ui.database import Project
    
    project_name = request.form.get('project_name', '').strip()
    if not project_name:
        flash('Project name is required', 'error')
        return redirect(url_for('manage_projects'))
    
    # Generate unique ID from name
    import re
    project_id = re.sub(r'[^a-z0-9_]', '_', project_name.lower())
    project_id = f"{current_user.id}_{project_id}"
    
    # Check if project already exists
    existing = Project.query.filter_by(id=project_id).first()
    if existing:
        flash(f'Project with similar name already exists', 'error')
        return redirect(url_for('manage_projects'))
    
    try:
        project = Project(
            id=project_id,
            user_id=current_user.id,
            name=project_name
        )
        db.session.add(project)
        db.session.commit()
        
        flash(f'Project "{project_name}" created successfully', 'success')
        # Auto-switch to new project
        session['current_project_id'] = project_id
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creating project: {e}")
        flash('Error creating project', 'error')
    
    return redirect(request.referrer or url_for('manage_projects'))


@app.route('/projects/<project_id>/switch')
@login_required
def switch_project(project_id):
    """Switch to a different project."""
    from ui.database import Project
    
    # Verify project belongs to user
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first()
    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('manage_projects'))
    
    session['current_project_id'] = project_id
    flash(f'Switched to project "{project.name}"', 'success')
    return redirect(url_for('index'))


@app.route('/projects/<project_id>/rename', methods=['POST'])
@login_required
def rename_project(project_id):
    """Rename a project."""
    from ui.database import Project
    
    data = request.get_json() if request.is_json else {}
    new_name = data.get('name', '').strip()
    
    if not new_name:
        return jsonify({'success': False, 'error': 'Name is required'}), 400
    
    # Verify project belongs to user
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first()
    if not project:
        return jsonify({'success': False, 'error': 'Project not found'}), 404
    
    try:
        project.name = new_name
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error renaming project: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/projects/<project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    """Delete a project and all its references."""
    from ui.database import Project
    
    # Verify project belongs to user
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first()
    if not project:
        return jsonify({'success': False, 'error': 'Project not found'}), 404
    
    try:
        project_name = project.name
        db.session.delete(project)
        db.session.commit()
        
        # If this was the current project, switch to another
        if session.get('current_project_id') == project_id:
            remaining = Project.query.filter_by(user_id=current_user.id).first()
            session['current_project_id'] = remaining.id if remaining else None
        
        return jsonify({'success': True, 'message': f'Deleted project "{project_name}"'})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting project: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/compliance/history")
@login_required
def compliance_history():
    """View saved compliance reports for the current project."""
    project_id = session.get('current_project_id')
    if not project_id:
        flash("Please select a project first.", "info")
        return redirect(url_for('manage_projects'))
    
    reports = SavedComplianceReport.query.filter_by(project_id=project_id).order_by(SavedComplianceReport.created_at.desc()).all()
    
    return render_template("compliance_history.html", reports=reports)

@app.route("/compliance/view/<int:report_id>")
@login_required
def view_saved_report(report_id):
    """View a specific saved compliance report."""
    report = SavedComplianceReport.query.get_or_404(report_id)
    
    # Security: check project belongs to user
    from ui.database import Project
    project = Project.query.get(report.project_id)
    if not project or project.user_id != current_user.id:
        flash("Permission denied.", "error")
        return redirect(url_for('compliance_history'))
    
    # Restore the result dict from JSON
    try:
        result = json.loads(report.report_data)
        # origin 'history' to adjust navigation in template (legacy key but useful)
        return render_template("compliance_report.html", result=result, origin='history', saved_report=report)
    except Exception as e:
        app.logger.error(f"Error loading saved report data: {e}")
        flash("Error loading report data.", "error")
        return redirect(url_for('compliance_history'))

@app.route("/compliance/delete/<int:report_id>", methods=["POST"])
@login_required
def delete_saved_report(report_id):
    """Delete a saved compliance report."""
    report = SavedComplianceReport.query.get_or_404(report_id)
    
    # Security check
    from ui.database import Project
    project = Project.query.get(report.project_id)
    if not project or project.user_id != current_user.id:
        flash("Permission denied.", "error")
        return redirect(url_for('compliance_history'))
    
    try:
        db.session.delete(report)
        db.session.commit()
        flash("Report deleted.")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting report: {e}")
        flash("Error deleting report.", "error")
        
    return redirect(url_for('compliance_history'))


# ============================================================================
# PROJECT CONTEXT PROCESSOR
# ============================================================================

@app.context_processor
def inject_project_context():
    """Inject current project data into all templates."""
    if not current_user.is_authenticated:
        return {
            'current_project': None,
            'available_projects': []
        }
    
    from ui.database import Project
    
    # Get current project ID from session
    current_project_id = session.get('current_project_id')
    
    # Get all projects for user
    all_projects = Project.query.filter_by(user_id=current_user.id).all()
    
    # If no current project or doesn't exist, use first available
    current_project = None
    if current_project_id:
        current_project = Project.query.filter_by(
            id=current_project_id, 
            user_id=current_user.id
        ).first()
    
    if not current_project and all_projects:
        current_project = all_projects[0]
        session['current_project_id'] = current_project.id
    
    # Convert to dicts for template
    return {
        'current_project': current_project.to_dict() if current_project else None,
        'available_projects': [p.to_dict() for p in all_projects]
    }


# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error='Page not found', error_code=404), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error='Internal server error', error_code=500), 500



if __name__ == "__main__":
    # In production, use a production WSGI server like Gunicorn
    app.run(debug=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true')
