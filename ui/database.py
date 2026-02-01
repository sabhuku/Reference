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
            'doi': self.doi
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
