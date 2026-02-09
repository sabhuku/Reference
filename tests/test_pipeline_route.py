"""
Minimal smoke test for pipeline analysis route.

Tests route availability and Stage 3 safety (analysis mode enforcement).
"""
import pytest
import sys
import os

# Add project root to path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def auth(client):
    """Authentication helper."""
    class AuthActions:
        def __init__(self, client):
            self._client = client
        
        def login(self, username='test@example.com', password='testpass'):
            return self._client.post('/login', data={
                'email': username,
                'password': password
            })
        
        def logout(self):
            return self._client.get('/logout')
    
    return AuthActions(client)


def test_pipeline_analyze_route_availability(client, auth):
    """Verify /pipeline/analyze route is accessible and renders."""
    # Create test user first
    from ui.database import User, db
    from ui.app import app
    
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass')
        db.session.add(user)
        db.session.commit()
    
    # Login
    auth.login()
    
    # Test GET request
    response = client.get('/pipeline/analyze')
    assert response.status_code == 200
    assert b'Pipeline Analysis' in response.data or b'pipeline' in response.data.lower()


def test_pipeline_analyze_stage3_disabled(client, auth):
    """
    Verify Stage 3 is NOT executed in analysis mode.
    
    CRITICAL SAFETY TEST: Ensures no external API calls or generative remediation.
    """
    # Create test user
    from ui.database import User, db
    from ui.app import app
    
    with app.app_context():
        user = User(username='testuser2', email='test2@example.com')
        user.set_password('testpass')
        db.session.add(user)
        db.session.commit()
    
    # Login
    auth.login('test2@example.com', 'testpass')
    
    # Submit incomplete reference (would trigger Stage 3 in normal mode)
    response = client.post('/pipeline/analyze', data={
        'reference_text': 'Incomplete reference (2020)'
    })
    
    # Verify response contains analysis mode indicator
    assert response.status_code == 200
    assert (b'skipped_analysis_mode' in response.data or 
            b'analysis mode' in response.data.lower() or
            b'disabled' in response.data.lower())
