import os
import json
import unittest
from ui import app as ui_app

TEST_PERSIST = os.path.abspath(os.path.join(os.path.dirname(__file__), 'manual_refs_test.json'))

class IntegrationUITest(unittest.TestCase):
    def setUp(self):
        # direct the app to use a test persistence file
        ui_app.PERSIST_PATH = TEST_PERSIST
        # ensure clean start
        try:
            os.remove(TEST_PERSIST)
        except OSError:
            pass
        self.app = ui_app.app.test_client()
        self.app.testing = True

    def tearDown(self):
        try:
            os.remove(TEST_PERSIST)
        except OSError:
            pass

    def test_manual_add_edit_remove_flow(self):
        # add
        resp = self.app.post('/manual_add', data={
            'title': 'Test Title',
            'authors': 'John Smith',
            'year': '2020',
            'journal': 'Journal',
            'publisher': 'Pub',
            'volume': '1',
            'issue': '2',
            'pages': '10-20',
            'doi': '10.1234/test',
            'pub_type': 'article'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # ensure file saved
        with open(TEST_PERSIST, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], 'Test Title')

        # edit
        resp = self.app.post('/edit/0', data={
            'title': 'Updated Title',
            'authors': 'Jane Doe',
            'year': '2021',
            'journal': 'Journal2',
            'publisher': 'Pub2',
            'volume': '3',
            'issue': '4',
            'pages': '30-40',
            'doi': '10.9999/updated',
            'pub_type': 'article'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        with open(TEST_PERSIST, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.assertEqual(data[0]['title'], 'Updated Title')

        # remove
        resp = self.app.post('/remove/0', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        with open(TEST_PERSIST, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.assertEqual(len(data), 0)

if __name__ == '__main__':
    unittest.main()
