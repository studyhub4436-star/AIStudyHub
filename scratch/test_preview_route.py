import unittest
import os
import json
from bson.objectid import ObjectId
from app import app, db, users_col, docs_col, downloads_col, otps_col

class PreviewRouteTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        
        # Insert mock user
        self.user_id = users_col.insert_one({
            'name': 'Test User',
            'email': 'test@sasi.ac.in',
            'password_hash': 'xxx',
            'branch': 'CSE',
            'year': '3rd Year'
        }).inserted_id

        # Insert mock document
        self.doc_id = docs_col.insert_one({
            'title': 'Test PDF Document',
            'filename': 'test_doc_preview.pdf',
            'downloads_count': 0
        }).inserted_id

        # Create dummy file to avoid 404
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        self.dummy_file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'test_doc_preview.pdf')
        with open(self.dummy_file_path, 'w') as f:
            f.write('%PDF-1.7 dummy pdf content')

    def tearDown(self):
        # Clean up database
        users_col.delete_one({'_id': self.user_id})
        docs_col.delete_one({'_id': self.doc_id})
        
        # Clean up dummy file
        if os.path.exists(self.dummy_file_path):
            os.remove(self.dummy_file_path)

    def test_preview_success(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = str(self.user_id)

        response = self.client.get(f'/preview/{self.doc_id}')
        print("PREVIEW STATUS:", response.status_code)
        print("PREVIEW HEADERS:", dict(response.headers))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('Content-Type'), 'application/pdf')

if __name__ == '__main__':
    unittest.main()
