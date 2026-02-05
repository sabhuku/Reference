"""
Shared pytest fixtures for AI remediation tests.
"""
import pytest
import sys
import os

# Add project root to path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ui.database import db, Reference


@pytest.fixture
def app():
    """Create Flask app for testing."""
    # Import app after path setup
    from ui import app as flask_app
    
    # Configure for testing
    flask_app.app.config['TESTING'] = True
    flask_app.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    flask_app.app.config['WTF_CSRF_ENABLED'] = False
    
    with flask_app.app.app_context():
        db.create_all()
        yield flask_app.app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def test_reference(app):
    """Create a test reference for canonical guard tests."""
    with app.app_context():
        ref = Reference(
            bibliography_id=1,
            source='test',
            pub_type='journal-article',
            title='Test Article',
            authors='["Smith, John"]',
            year='2023',
            journal='Test Journal',
            publisher='Test Publisher'
        )
        db.session.add(ref)
        db.session.commit()
        yield ref
        db.session.delete(ref)
        db.session.commit()
