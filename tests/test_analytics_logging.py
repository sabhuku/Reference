import pytest
import json
import os
from pathlib import Path
from ui.app import app
from src.analytics import ANALYTICS_FILE

class TestAnalyticsLogging:
    @pytest.fixture
    def client(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        with app.test_client() as client:
            yield client

    def test_log_edit_and_compliace(self, client):
        # 1. Clear or record start size of log file
        start_size = 0
        if ANALYTICS_FILE.exists():
            start_size = ANALYTICS_FILE.stat().st_size
            
        print(f"Log file: {ANALYTICS_FILE}")
        
        # 2. Inject a reference
        with client.session_transaction() as sess:
            sess['refs'] = [{
                'source': 'manual',
                'pub_type': 'book',
                'title': 'Original Title',
                'authors': ['Author, A.'],
                'year': '2023',
                'publisher': 'Pub',
                'location': 'Loc'
            }]
            
        # 3. Perform Edit
        rv = client.post('/edit/0', data={
            'title': 'Edited Title',
            'authors': 'Author, A.',
            'year': '2023',
            'pub_type': 'book',
            'publisher': 'Pub',
            'journal': '',
            'volume': '',
            'issue': '',
            'pages': '',
            'doi': ''
        }, follow_redirects=True)
        assert rv.status_code == 200
        
        # 4. Perform Compliance Check
        # /compliance leads to a render, we just need to ensure it runs without error
        rv = client.get('/compliance?origin=bibliography')
        assert rv.status_code == 200
        
        # 5. Verify Log File Content
        assert ANALYTICS_FILE.exists()
        end_size = ANALYTICS_FILE.stat().st_size
        assert end_size > start_size, "Log file did not grow"
        
        # Read new lines
        with open(ANALYTICS_FILE, 'r', encoding='utf-8') as f:
            f.seek(start_size)
            new_content = f.read()
            
        print("NEW LOGS:\n", new_content)
        
        assert "reference_edited" in new_content
        assert "Original Title" in new_content # Old state
        assert "Edited Title" in new_content # New state
        
        assert "compliance_report_generated" in new_content
        assert "overall_score" in new_content
