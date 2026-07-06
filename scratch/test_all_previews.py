import os
import sys
sys.path.append('.')
from bson.objectid import ObjectId
from app import app, db, docs_col, users_col

# Setup test client
app.config['TESTING'] = True
client = app.test_client()

def test_previews():
    # Find a user to log in as
    user = users_col.find_one()
    if not user:
        print("No users found in database to simulate session!")
        return
    
    user_id = str(user['_id'])
    print(f"Simulating session for user: {user.get('email')} (ID: {user_id})")

    # Find all documents
    documents = list(docs_col.find())
    print(f"Found {len(documents)} documents in database.")

    for doc in documents:
        doc_id = str(doc['_id'])
        title = doc.get('title')
        filename = doc.get('filename')
        
        # Test preview route
        with client.session_transaction() as sess:
            sess['user_id'] = user_id

        response = client.get(f'/preview/{doc_id}')
        print(f"Doc: {title} | Filename: {filename} | ID: {doc_id}")
        print(f"  Response Status: {response.status_code}")
        print(f"  Content-Type: {response.headers.get('Content-Type')}")
        print(f"  Content-Disposition: {response.headers.get('Content-Disposition')}")
        if response.status_code != 200:
            print(f"  ERROR/WARNING: Response data snippet: {response.data[:200]}")
        print("-" * 50)

if __name__ == '__main__':
    test_previews()
