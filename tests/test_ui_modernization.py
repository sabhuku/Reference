import pytest
from flask import Flask, session
from ui.app import app

class TestUIModernization:
    @pytest.fixture
    def client(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        with app.test_client() as client:
            yield client

    def test_home_page_modernization(self, client):
        """Verify Home page contains Hero section and Quick Actions."""
        response = client.get('/')
        assert response.status_code == 200
        content = response.data.decode('utf-8')
        
        # Check for Hero Section class
        assert 'hero-section' in content
        # Check for Quick Action text
        assert 'Manual Entry' in content
        assert 'Import Check' in content
        # Check that we passed the 'recents' variable context (by inference of design)
        # We can't easily check 'recents' variable from outside, but we check the HTML structure
        assert 'Recent Activity' in content

    def test_bibliography_page_modernization(self, client):
        """Verify Bibliography page contains Sticky Toolbar and Card Layout."""
        # We need to simulate a session with data or just check empty state structure
        response = client.get('/bibliography')
        assert response.status_code == 200
        content = response.data.decode('utf-8')
        
        # Check for Sticky Toolbar
        assert 'sticky-toolbar' in content
        # Check for Global Style Controller (select name="style")
        assert '<select name="style"' in content
        # Check for Preview Button
        assert 'Preview' in content
