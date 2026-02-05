"""
Database models for user accounts and bibliographies.
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for authentication."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    bibliographies = db.relationship('Bibliography', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set user password."""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    def check_password(self, password):
        """Verify password against hash."""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Project(db.Model):
    """Project model for organizing references into collections."""
    __tablename__ = 'projects'
    
    id = db.Column(db.String(255), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_modified = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project_references = db.relationship('ProjectReference', backref='project', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert project to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_modified': self.last_modified.isoformat() if self.last_modified else None,
            'ref_count': len(self.project_references)
        }
    
    def __repr__(self):
        return f'<Project {self.name}>'


class ProjectReference(db.Model):
    """Reference stored within a project."""
    __tablename__ = 'project_references'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.String(255), db.ForeignKey('projects.id'), nullable=False, index=True)
    
    # Reference data (matching Publication dataclass structure)
    source = db.Column(db.String(50))
    pub_type = db.Column(db.String(50))
    title = db.Column(db.Text, nullable=False)
    authors = db.Column(db.Text)  # JSON string array
    year = db.Column(db.String(20))
    journal = db.Column(db.String(300))
    publisher = db.Column(db.String(200))
    location = db.Column(db.String(200))
    volume = db.Column(db.String(50))
    issue = db.Column(db.String(50))
    pages = db.Column(db.String(50))
    doi = db.Column(db.String(200), index=True)
    isbn = db.Column(db.String(20))
    url = db.Column(db.Text)
    access_date = db.Column(db.String(50))
    edition = db.Column(db.String(50))
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_publication_dict(self):
        """Convert to Publication-compatible dictionary."""
        return {
            'id': self.id,
            'source': self.source or '',
            'pub_type': self.pub_type or '',
            'title': self.title,
            'authors': json.loads(self.authors) if self.authors else [],
            'year': self.year or '',
            'journal': self.journal or '',
            'publisher': self.publisher or '',
            'location': self.location or '',
            'volume': self.volume or '',
            'issue': self.issue or '',
            'pages': self.pages or '',
            'doi': self.doi or '',
            'isbn': self.isbn or '',
            'url': self.url or '',
            'access_date': self.access_date or '',
            'edition': self.edition or ''
        }
    
    @staticmethod
    def from_publication(pub_dict, project_id):
        """Create ProjectReference from Publication dictionary."""
        return ProjectReference(
            project_id=project_id,
            source=pub_dict.get('source', ''),
            pub_type=pub_dict.get('pub_type', ''),
            title=pub_dict.get('title', ''),
            authors=json.dumps(pub_dict.get('authors', [])),
            year=pub_dict.get('year', ''),
            journal=pub_dict.get('journal', ''),
            publisher=pub_dict.get('publisher', ''),
            location=pub_dict.get('location', ''),
            volume=pub_dict.get('volume', ''),
            issue=pub_dict.get('issue', ''),
            pages=pub_dict.get('pages', ''),
            doi=pub_dict.get('doi', ''),
            isbn=pub_dict.get('isbn', ''),
            url=pub_dict.get('url', ''),
            access_date=pub_dict.get('access_date', ''),
            edition=pub_dict.get('edition', '')
        )
    
    def __repr__(self):
        return f'<ProjectReference {self.title[:30]}...>'


class Bibliography(db.Model):
    """Bibliography model for managing reference collections."""
    __tablename__ = 'bibliographies'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    citation_style = db.Column(db.String(50), default='APA')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    references = db.relationship('Reference', backref='bibliography', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Bibliography {self.name}>'


class Reference(db.Model):
    """Reference model for storing citation data."""
    __tablename__ = 'references'
    
    id = db.Column(db.Integer, primary_key=True)
    bibliography_id = db.Column(db.Integer, db.ForeignKey('bibliographies.id'), nullable=False, index=True)
    
    # Reference metadata
    source = db.Column(db.String(50))  # 'crossref', 'pubmed', 'manual', etc.
    pub_type = db.Column(db.String(50))
    title = db.Column(db.Text, nullable=False)
    authors = db.Column(db.Text)  # JSON string
    year = db.Column(db.String(20))
    journal = db.Column(db.String(300))
    publisher = db.Column(db.String(200))
    location = db.Column(db.String(200))  # Publisher location
    volume = db.Column(db.String(50))
    issue = db.Column(db.String(50))
    pages = db.Column(db.String(50))
    doi = db.Column(db.String(200), index=True)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert reference to dictionary (for API/session compatibility)."""
        return {
            'id': self.id,
            'source': self.source,
            'pub_type': self.pub_type,
            'title': self.title,
            'authors': json.loads(self.authors) if self.authors else [],
            'year': self.year,
            'journal': self.journal,
            'publisher': self.publisher,
            'volume': self.volume,
            'issue': self.issue,
            'pages': self.pages,
            'doi': self.doi,
            'added_at': self.added_at.isoformat() if self.added_at else None
        }
    
    @staticmethod
    def from_dict(data):
        """Create Reference from dictionary."""
        return Reference(
            source=data.get('source'),
            pub_type=data.get('pub_type'),
            title=data.get('title'),
            authors=json.dumps(data.get('authors', [])),
            year=data.get('year'),
            journal=data.get('journal'),
            publisher=data.get('publisher'),
            volume=data.get('volume'),
            issue=data.get('issue'),
            pages=data.get('pages'),
            doi=data.get('doi')
        )
    
    def __repr__(self):
        return f'<Reference {self.title[:30]}...>'
