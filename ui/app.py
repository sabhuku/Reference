from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify, Response
import json
import os
import io
import sys
import csv
from functools import wraps
from datetime import datetime
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from io import StringIO
from werkzeug.utils import secure_filename
import portalocker
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
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

# Import database models
from ui.database import db, User, Bibliography, Reference as DBReference

from src.referencing import referencing

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
    """Normalize a free-form authors string into a list of 'Surname, Given' entries.

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
        return {"authors": [], "confidence": 1.0, "ambiguous": False, "parsing_method": "empty"} if return_metadata else []
    
    s = raw.strip()
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
    except Exception:
        return "Error formatting reference"

@app.errorhandler(400)
def bad_request_error(e):
    app.logger.error(f"Bad Request Error: {str(e)}")
    flash("Bad request. Please try again.", "error")
    return redirect(request.referrer or url_for("index"))

# Helpers
def get_session_refs():
    # If user is authenticated, return their database references
    if current_user.is_authenticated:
        # Get default bibliography
        default_bib = Bibliography.query.filter_by(
            user_id=current_user.id,
            name='My Bibliography'
        ).first()
        if default_bib:
            return [r.to_dict() for r in default_bib.references]
        return []

    refs = session.get("refs")
    if refs is None:
        # Try to pre-populate from persisted refs on first access
        refs = load_persisted_refs()
        session["refs"] = refs
    return refs

from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, IntegerField, BooleanField
from wtforms.validators import DataRequired, Optional, NumberRange, Length, Regexp, ValidationError
from datetime import datetime

class SearchForm(FlaskForm):
    # Basic search fields
    query = StringField('Query', validators=[DataRequired()], 
                       render_kw={"placeholder": "Search by title, author, or keywords"})
    stype = SelectField('Type', choices=[
        ('title', 'Title / keywords'), 
        ('author', 'Author'),
        ('doi', 'DOI')
    ])
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
@limiter.limit("10 per minute")  # Allow 10 requests per minute
@limiter.limit("200 per day")   # And 200 requests per day
def index():
    form = SearchForm()
    refs = get_session_refs()
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
                # For title search
                # Pass filters directly to the retrieval layer
                results = ref_manager.search_works(
                    query, 
                    **filters
                ) or []
                
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
    
    # Filter out duplicates for display (defensive redundancy)
    refs = referencing.dedupe(refs)
    
    # Pagination for home page references
    page = request.args.get('page', 1, type=int)
    per_page = 10
    total_refs = len(refs)
    total_pages = (total_refs + per_page - 1) // per_page if total_refs > 0 else 1
    
    # Slice references for the current page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    # Store references with their original indices
    paginated_refs = []
    for i, ref in enumerate(refs):
        if start_idx <= i < end_idx:
            paginated_refs.append({'data': ref, 'original_index': i})
    
    # Add current year for the year range fields
    current_year = datetime.now().year
    
    return render_template("index.html", 
                         refs=paginated_refs, 
                         style=style, 
                         form=form,
                         current_year=current_year,
                         page=page,
                         total_pages=total_pages,
                         total_refs=total_refs)


class ManualForm(FlaskForm):
    title = StringField('Title', validators=[
        DataRequired(message="Title is required"),
        Length(min=1, max=500, message="Title must be between 1 and 500 characters")
    ])
    
    authors = StringField(
        'Authors (comma-separated, e.g. "Smith, J., Doe, A.")',
        validators=[
            Optional(),
            Length(max=1000, message="Authors field is too long (max 1000 characters)")
        ]
    )
    
    year = StringField('Year', validators=[
        Optional(),
        Regexp(r'^\d{4}$', message="Year must be 4 digits (e.g., 2023)")
    ])
    
    journal = StringField('Journal / Publisher', validators=[
        Optional(),
        Length(max=300, message="Journal name is too long (max 300 characters)")
    ])
    
    publisher = StringField('Publisher (for books)', validators=[
        Optional(),
        Length(max=200, message="Publisher name is too long (max 200 characters)")
    ])
    
    volume = StringField('Volume', validators=[
        Optional(),
        Length(max=20, message="Volume is too long (max 20 characters)")
    ])
    
    issue = StringField('Issue', validators=[
        Optional(),
        Length(max=20, message="Issue is too long (max 20 characters)")
    ])
    
    pages = StringField('Pages', validators=[
        Optional(),
        Regexp(r'^[\d\-–]+$', message="Pages must be numbers or ranges (e.g., 25-30)")
    ])
    
    doi = StringField('DOI', validators=[
        Optional(),
        Regexp(
            r'^10\.\d{4,9}/[\S]+$',
            message="Invalid DOI format (should start with 10., e.g., 10.1234/example)"
        )
    ])
    
    pub_type = SelectField('Type', choices=[
        ('book', 'Book'), 
        ('journal-article', 'Journal Article'),
        ('proceedings-article', 'Proceedings Article')
    ])
    
    submit = SubmitField('Add Reference')


# Authentication Forms
from wtforms import PasswordField
from wtforms.validators import Email, EqualTo

class RegistrationForm(FlaskForm):
    """User registration form."""
    username = StringField('Username', validators=[
        DataRequired(message="Username is required"),
        Length(min=3, max=80, message="Username must be between 3 and 80 characters")
    ])
    
    email = StringField('Email', validators=[
        DataRequired(message="Email is required"),
        Email(message="Invalid email address"),
        Length(max=120, message="Email is too long")
    ])
    
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required"),
        Length(min=8, message="Password must be at least 8 characters")
    ])
    
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message="Please confirm your password"),
        EqualTo('password', message="Passwords must match")
    ])
    
    submit = SubmitField('Sign Up')


class LoginForm(FlaskForm):
    """User login form."""
    email = StringField('Email', validators=[
        DataRequired(message="Email is required"),
        Email(message="Invalid email address")
    ])
    
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required")
    ])
    
    remember = BooleanField('Remember Me')
    
    submit = SubmitField('Log In')

@app.route('/manual', methods=['GET'])
def manual():
    """Render the manual entry form."""
    form = ManualForm()
    return render_template('manual.html', form=form)


@app.route('/manual_add', methods=['POST'])
def manual_add():
    """Handle manual reference submission with validation."""
    form = ManualForm()
    
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
            # Add to database
            default_bib = Bibliography.query.filter_by(
                user_id=current_user.id,
                name='My Bibliography'
            ).first()
            if not default_bib:
                default_bib = Bibliography(user_id=current_user.id, name='My Bibliography')
                db.session.add(default_bib)
                db.session.commit()
            
            ref = DBReference.from_dict(pub)
            ref.bibliography_id = default_bib.id
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
            
            # Migrate session refs if any
            session_refs = session.get('refs', [])
            if session_refs:
                try:
                    default_bib = Bibliography.query.filter_by(
                        user_id=user.id,
                        name='My Bibliography'
                    ).first()
                    
                    if not default_bib:
                        default_bib = Bibliography(
                            user_id=user.id,
                            name='My Bibliography'
                        )
                        db.session.add(default_bib)
                        db.session.commit()
                    
                    existing_refs = [r.to_dict() for r in default_bib.references]
                    
                    added_count = 0
                    for ref_dict in session_refs:
                        if not referencing.is_duplicate(ref_dict, existing_refs):
                            ref = DBReference.from_dict(ref_dict)
                            ref.bibliography_id = default_bib.id
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
        flash(f'Bibliography "{bib_name}" deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting bibliography: {e}")
        flash('Error deleting bibliography', 'error')
    
    return redirect(url_for('bibliographies'))


@app.route('/remove/<int:idx>', methods=['GET', 'POST'])
def remove(idx):
    refs = get_session_refs()
    if 0 <= idx < len(refs):
        refs.pop(idx)
        session['refs'] = refs
        save_persisted_refs(refs)
        flash('Removed item')
    else:
        flash('Invalid index')
    return redirect(url_for('bibliography'))


@app.route('/edit/<int:idx>', methods=['GET', 'POST'])
def edit(idx):
    refs = get_session_refs()
    if request.method == 'GET':
        if 0 <= idx < len(refs):
            pub = refs[idx]
            return render_template('manual.html', edit=True, idx=idx, pub=pub)
        flash('Invalid index')
        return redirect(url_for('bibliography'))

    # POST: update
    if 0 <= idx < len(refs):
        title = request.form.get('title', '').strip()
        authors_raw = request.form.get('authors', '').strip()
        year = request.form.get('year', '').strip()
        journal = request.form.get('journal', '').strip()
        publisher = request.form.get('publisher', '').strip()
        volume = request.form.get('volume', '').strip()
        issue = request.form.get('issue', '').strip()
        pages = request.form.get('pages', '').strip()
        doi = request.form.get('doi', '').strip()
        pub_type = request.form.get('pub_type', 'book')

        if not title:
            flash('Title is required')
            return redirect(url_for('edit', idx=idx))

        authors = normalize_authors(authors_raw)
        pub = {
            'source': 'manual',
            'pub_type': pub_type,
            'authors': authors or [],
            'year': year or 'n.d.',
            'title': title,
            'journal': journal,
            'publisher': publisher,
            'location': '',
            'volume': volume,
            'issue': issue,
            'pages': pages,
            'doi': doi,
        }
        refs[idx] = pub
        session['refs'] = refs
        save_persisted_refs(refs)
        flash('Reference updated')
    else:
        flash('Invalid index')
    return redirect(url_for('bibliography'))

@app.route("/search", methods=["POST"])
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
            # Add to database
            default_bib = Bibliography.query.filter_by(
                user_id=current_user.id,
                name='My Bibliography'
            ).first()
            if not default_bib:
                default_bib = Bibliography(user_id=current_user.id, name='My Bibliography')
                db.session.add(default_bib)
                db.session.commit()
            
            ref = DBReference.from_dict(pub)
            ref.bibliography_id = default_bib.id
            db.session.add(ref)
            db.session.commit()
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
        return render_template("compliance_report.html", result=result, origin=origin)
    except Exception as e:
        app.logger.error(f"Compliance check failed: {e}")
        flash("Error running compliance check.", "error")
        return redirect(url_for('bibliography'))

@app.route("/bibliography", methods=["GET"])
@limiter.limit("10 per minute")  # Allow 10 requests per minute
@limiter.limit("200 per day")   # And 200 requests per day
def bibliography():
    refs = get_session_refs()
    style = request.args.get("style", session.get("style", "harvard"))
    session["style"] = style
    uniq = referencing.dedupe(refs)
    refs_sorted = referencing.sort_for_bibliography(uniq, style)
    return render_template("bibliography.html", refs=refs_sorted, style=style)

@app.route("/export_word", methods=["GET"])
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
        app.logger.error(f"Export error: {str(e)}")
        flash(f"Error exporting file: {str(e)}", "error")
        return redirect(url_for("bibliography"))

@app.route("/import", methods=["GET", "POST"])
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
                # We can just render the compliance report
                flash(f"Successfully imported and checked {len(imported_pubs)} references.", "success")
                return render_template("compliance_report.html", result=result, origin='index')
                
            except Exception as e:
                app.logger.error(f"Import error: {e}")
                flash('An error occurred during import.', 'error')
                return redirect(request.url)

    return render_template("import.html")

# Simple health route
@app.route("/health", methods=["GET"])
def health():
    return "ok", 200

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
