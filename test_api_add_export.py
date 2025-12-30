import os
import json
import tempfile
import unittest
from unittest.mock import patch
from ui import app as ui_app

class APISmokeTest(unittest.TestCase):
    def setUp(self):
        # Use a temp file for persistence and a temp folder for downloads
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_persist = os.path.join(self.temp_dir.name, 'manual_refs_test.json')
        ui_app.PERSIST_PATH = self.test_persist
        # patch referencing DOWNLOAD_FOLDER during tests
        import referencing
        self.orig_download = referencing.DOWNLOAD_FOLDER if hasattr(referencing, 'DOWNLOAD_FOLDER') else None
        referencing.DOWNLOAD_FOLDER = self.temp_dir.name
        self.client = ui_app.app.test_client()
        self.client.testing = True

    def tearDown(self):
        import referencing
        if self.orig_download is not None:
            referencing.DOWNLOAD_FOLDER = self.orig_download
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_search_add_and_export_flow(self):
        fake_pub = {
            'source': 'mock',
            'pub_type': 'article',
            'authors': ['Smith, John'],
            'year': '2022',
            'title': 'Mock Title',
            'journal': 'Mock Journal',
            'publisher': 'Mock Pub',
            'location': '',
            'volume': '1',
            'issue': '1',
            'pages': '1-2',
            'doi': '10.0000/mock'
        }

        # Mock the lookup_single_work to return our fake
        with patch('referencing.lookup_single_work', return_value=fake_pub):
            # perform a search POST which renders results (we assert 200)
            resp = self.client.post('/search', data={'query': 'mock', 'stype': 'title'}, follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            # Simulate clicking add by posting to /add with the pub JSON
            resp = self.client.post('/add', data={'pub': json.dumps(fake_pub)}, follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            # Now mock save_references_to_word to create a small file and return its path
            def fake_save(refs_sorted, download_folder, filename, _set, style):
                path = os.path.join(download_folder, 'refs_test.docx')
                with open(path, 'wb') as f:
                    f.write(b'PK\x03\x04')  # write minimal bytes resembling a zip/docx
                return path

            with patch('referencing.save_references_to_word', side_effect=fake_save):
                resp = self.client.get('/export')
                # If send_file works, we get a 200; if not, we may be redirected but still 200 due to follow
                self.assertIn(resp.status_code, (200,))

if __name__ == '__main__':
    unittest.main()
