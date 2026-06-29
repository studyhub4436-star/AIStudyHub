import unittest
import os
import json
from datetime import datetime, timezone
from bson.objectid import ObjectId
from app import app, db, users_col, docs_col, downloads_col, otps_col

class AIStudyHubTestCase(unittest.TestCase):
    def setUp(self):
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        
        # We will use a separate test database name
        self.original_db_name = db.name
        self.test_db_name = 'aistudyhub_test'
        
        # Point collections to the test database
        test_db = db.client[self.test_db_name]
        self.test_users = test_db['users']
        self.test_docs = test_db['documents']
        self.test_downloads = test_db['downloads']
        self.test_otps = test_db['otps']
        
        # Override app collections
        global users_col, docs_col, downloads_col, otps_col
        import app as app_module
        self.orig_users = app_module.users_col
        self.orig_docs = app_module.docs_col
        self.orig_dls = app_module.downloads_col
        self.orig_otps = app_module.otps_col
        
        self.orig_send_otp = app_module.send_email_otp
        app_module.send_email_otp = lambda to, otp: True

        app_module.users_col = self.test_users
        app_module.docs_col = self.test_docs
        app_module.downloads_col = self.test_downloads
        app_module.otps_col = self.test_otps
        
        # Clear collections
        self.test_users.delete_many({})
        self.test_docs.delete_many({})
        self.test_downloads.delete_many({})
        self.test_otps.delete_many({})

    def tearDown(self):
        # Drop test database
        db.client.drop_database(self.test_db_name)
        
        # Restore original collections and helper
        import app as app_module
        app_module.users_col = self.orig_users
        app_module.docs_col = self.orig_docs
        app_module.downloads_col = self.orig_dls
        app_module.otps_col = self.orig_otps
        app_module.send_email_otp = self.orig_send_otp

    def test_pages_load(self):
        """Test that static pages render HTML correctly."""
        for path in ['/', '/login', '/register']:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)

    def test_otp_generation(self):
        """Test OTP generation and database storage."""
        response = self.client.post('/api/send-otp', 
                                   data=json.dumps({'email': 'test@example.com'}),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
        # Check database
        record = self.test_otps.find_one({'email': 'test@example.com'})
        self.assertIsNotNone(record)
        self.assertEqual(len(record['otp']), 6)

    def test_registration_and_login(self):
        """Test user registration flow and login verify."""
        # 1. Send OTP
        self.client.post('/api/send-otp', 
                         data=json.dumps({'email': 'testuser@example.com'}),
                         content_type='application/json')
        otp_record = self.test_otps.find_one({'email': 'testuser@example.com'})
        otp = otp_record['otp']
        
        # 2. Register User
        reg_payload = {
            'name': 'Test User',
            'email': 'testuser@example.com',
            'password': 'password123',
            'branch': 'CSE',
            'year': '3rd Year',
            'otp': otp
        }
        reg_response = self.client.post('/api/register',
                                        data=json.dumps(reg_payload),
                                        content_type='application/json')
        self.assertEqual(reg_response.status_code, 200)
        reg_data = json.loads(reg_response.data)
        self.assertTrue(reg_data['success'])
        
        # Check user database record
        user = self.test_users.find_one({'email': 'testuser@example.com'})
        self.assertIsNotNone(user)
        self.assertEqual(user['name'], 'Test User')
        
        # 3. Login
        login_payload = {
            'email': 'testuser@example.com',
            'password': 'password123'
        }
        login_response = self.client.post('/api/login',
                                          data=json.dumps(login_payload),
                                          content_type='application/json')
        self.assertEqual(login_response.status_code, 200)
        login_data = json.loads(login_response.data)
        self.assertTrue(login_data['success'])
        
        # Check session is set
        with self.client.session_transaction() as sess:
            self.assertIn('user_id', sess)
            self.assertEqual(sess['user_id'], str(user['_id']))

    def test_profile_update(self):
        """Test profile update API."""
        # Insert a mock user and set session
        user_id = self.test_users.insert_one({
            'name': 'Original Name',
            'email': 'original@example.com',
            'password_hash': 'xxx',
            'branch': 'CSE',
            'year': '2nd Year'
        }).inserted_id
        
        with self.client.session_transaction() as sess:
            sess['user_id'] = str(user_id)
            
        update_payload = {
            'name': 'Updated Name',
            'email': 'updated@example.com',
            'branch': 'IT',
            'year': '3rd Year'
        }
        response = self.client.post('/api/profile/update',
                                    data=json.dumps(update_payload),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
        # Verify database
        user = self.test_users.find_one({'_id': user_id})
        self.assertEqual(user['name'], 'Updated Name')
        self.assertEqual(user['email'], 'updated@example.com')
        self.assertEqual(user['branch'], 'IT')
        self.assertEqual(user['year'], '3rd Year')

if __name__ == '__main__':
    unittest.main()
