import os
import random
import string
from datetime import datetime, timezone, timedelta
from datetime import datetime, timezone
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_from_directory
from bson.objectid import ObjectId
from pymongo import MongoClient, ASCENDING
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import numpy as np
from datetime import datetime, timezone
def is_locked(pdf):
    lock_time = pdf.get("locked_until")
    if not lock_time:
        return False

    if lock_time.tzinfo is None:
        lock_time = lock_time.replace(tzinfo=timezone.utc)

    return datetime.now(timezone.utc) < lock_time
# Load environment variables
load_dotenv()

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.getenv('SECRET_KEY', 'default_super_secret_key_12345')
print("=" * 50)
print("MONGO_URI exists:", bool(os.getenv("MONGO_URI")))
print("MONGO_DB_NAME:", os.getenv("MONGO_DB_NAME"))
print("BREVO_API_KEY exists:", bool(os.getenv("BREVO_API_KEY")))
print("=" * 50)
# MongoDation
# MongoDation
MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'studyhub')

try:
    if not MONGO_URI:
        raise ValueError("MONGO_URI environment variable is missing or empty")

    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=10000,  # ⬅ important (10 sec)
        connectTimeoutMS=10000,
        socketTimeoutMS=10000,
        tls=True,
        retryWrites=True
    )

    client.admin.command('ping')  # force real connection test
    db = client[MONGO_DB_NAME]

    print("[DATABASE] Connected successfully to MongoDB")

except Exception as e:
    print(f"[DATABASE WARNING] Could not connect to MongoDB: {e}")
    print("[DATABASE WARNING] Falling back to mongomock (NO persistence)")
    import mongomock
    client = mongomock.MongoClient()
    db = client[MONGO_DB_NAME]

# Collections
users_col = db['users']
docs_col = db['documents']
downloads_col = db['downloads']
otps_col = db['otps']

# Indexes
users_col.create_index('email', unique=True)
# OTP TTL index: Expire OTP documents 300 seconds (5 minutes) after the 'created_at' field
otps_col.create_index('created_at', expireAfterSeconds=300)

# Folder Configuration
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Maximum file size = 50 MB
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

# Only PDF allowed
ALLOWED_EXTENSIONS = {'pdf', 'doc', "docx"}

def allowed_file(filename):
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )
# ==========================================
# SMTP Email Helper
# ==========================================
# ==========================================
# Brevo Email Helper
# ==========================================

def send_email_otp(email, otp):
    try:
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key["api-key"] = os.getenv("BREVO_API_KEY")

        api_client = sib_api_v3_sdk.ApiClient(configuration)
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(api_client)

        html = f"""
        <html>
        <body>
            <h2>Study Hub OTP Verification</h2>
            <p>Your OTP is:</p>
            <h1>{otp}</h1>
            <p>This OTP is valid for 5 minutes.</p>
        </body>
        </html>
        """

        email_data = sib_api_v3_sdk.SendSmtpEmail(
            sender={
                "name": "Study Hub",
                "email": "studyhub4436@gmail.com"
            },
            to=[{"email": email}],
            subject="Study Hub OTP Verification",
            html_content=html
        )

        api_instance.send_transac_email(email_data)
        return True

    except Exception as e:
        import traceback
        traceback.print_exc()
        print("Brevo Error:", repr(e))
    return False
# ==========================================
# Page Routes
# ==========================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')
@app.route('/forgot-password')
def forgot_password():
    return render_template('forgot_password.html')

@app.route('/register')
def register():
    return render_template('register.html')

# Compatibility Redirects
@app.route('/index.html')
def index_html_redirect():
    return redirect(url_for('index'))

@app.route('/login.html')
def login_html_redirect():
    return redirect(url_for('login'))

@app.route('/register.html')
def register_html_redirect():
    return redirect(url_for('register'))

@app.route('/dashboard.html')
def dashboard_html_redirect():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = users_col.find_one({'_id': ObjectId(session['user_id'])})
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    # Calculate stats
    total_pdfs = docs_col.count_documents({})
    
    # Total downloads across all documents
    total_downloads = downloads_col.count_documents({})
    
    # Trending files count (downloaded at least once)
    trending_count = docs_col.count_documents({'downloads_count': {'$gt': 0}})
    
    # User's own uploads
    my_uploads_count = docs_col.count_documents({'uploader_id': str(user['_id'])})
    
    # Fetch user download history
    # Join with documents collection to get details
    user_downloads_cursor = downloads_col.find({'user_id': str(user['_id'])}).sort('download_date', -1)
    downloads_history = []
    for dl in user_downloads_cursor:
        doc = docs_col.find_one({'_id': ObjectId(dl['document_id'])})
        if doc:
            downloads_history.append({
                'title': doc['title'],
                'subject': doc['subject'],
                'date': dl['download_date'].strftime('%d-%m-%Y')
            })
            
    # Fetch trending PDFs (top downloads)
    trending_cursor = docs_col.find({'downloads_count': {'$gt': 0}}).sort('downloads_count', -1).limit(4)
    trending_files = []
    for doc in trending_cursor:
        trending_files.append({
            'id': str(doc['_id']),
            'title': doc['title'],
            'downloads': doc['downloads_count']
        })
        
    # If no trending files, get latest uploads
    if not trending_files:
        latest_cursor = docs_col.find().sort('upload_date', -1).limit(4)
        for doc in latest_cursor:
            trending_files.append({
                'id': str(doc['_id']),
                'title': doc['title'],
                'downloads': doc['downloads_count']
            })

    # Fetch Recommendations (AI Recommended)
    recommended_files = get_recommendations(user)
    
    return render_template('dashboard.html', 
                           user=user, 
                           total_pdfs=total_pdfs, 
                           total_downloads=total_downloads, 
                           trending_count=trending_count, 
                           my_uploads_count=my_uploads_count,
                           trending_files=trending_files,
                           recommended_files=recommended_files,
                           downloads_history=downloads_history)
@app.route('/admin-dashboard')
def admin_dashboard():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    total_users = users_col.count_documents({})
    total_pdfs = docs_col.count_documents({})
    total_downloads = downloads_col.count_documents({})

    # PDFs
    pdfs_raw = list(docs_col.find().sort("upload_date", -1))
    pdfs = []

    for pdf in pdfs_raw:

        if is_locked(pdf):
            continue

        user = users_col.find_one({"_id": ObjectId(pdf["uploader_id"])})

        pdfs.append({
            "_id": pdf["_id"],
            "title": pdf.get("title", ""),
            "subject": pdf.get("subject", ""),
            "uploaded_by": user["email"] if user else "Unknown",
            "hidden": pdf.get("hidden", False)
        })

    # Users
    users = list(users_col.find())

    return render_template(
        'admin_dashboard.html',
        total_users=total_users,
        total_pdfs=total_pdfs,
        total_downloads=total_downloads,
        pdfs=pdfs,
        users=users
    )


@app.route('/admin/users')
def admin_users():

    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    users = list(users_col.find())

    return render_template(
        'admin_users.html',
        users=users
    )
@app.route('/admin/pdfs')
def admin_pdfs():

    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    pdfs_raw = list(docs_col.find().sort('upload_date', -1))

    pdfs = []

    for pdf in pdfs_raw:

        # 🔒 locked PDFs skip
        if is_locked(pdf):
            continue

        user = users_col.find_one({'_id': ObjectId(pdf['uploader_id'])})

        pdfs.append({
            '_id': pdf['_id'],
            'title': pdf.get('title', ''),
            'subject': pdf.get('subject', ''),
            'uploaded_by': user['email'] if user else 'Unknown',
            'hidden': pdf.get('hidden', False)
        })

    return render_template('admin_pdfs.html', pdfs=pdfs)
@app.route('/admin/preview/<doc_id>')
def admin_preview(doc_id):

    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))
    doc = docs_col.find_one({'_id': ObjectId(doc_id)})

    if not doc:
        return "File Not Found", 404

    # 🔒 START LOCK (20 minutes)
    docs_col.update_one(
        {'_id': ObjectId(doc_id)},
        {'$set': {
            'locked_until': datetime.now(timezone.utc) + timedelta(minutes=20)
        }}
    )

    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        doc['filename']
    )
@app.route('/admin/delete-pdf/<doc_id>')
def admin_delete_pdf(doc_id):

    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    doc = docs_col.find_one({
        '_id': ObjectId(doc_id)
    })

    if doc:

        filepath = os.path.join(
            app.config['UPLOAD_FOLDER'],
            doc['filename']
        )

        if os.path.exists(filepath):
            os.remove(filepath)

        docs_col.delete_one({
            '_id': ObjectId(doc_id)
        })

        downloads_col.delete_many({
            'document_id': doc_id
        })

    return redirect(url_for('admin_dashboard'))
@app.route('/admin/hide-pdf/<doc_id>')
def hide_pdf(doc_id):

    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    docs_col.update_one(
        {'_id': ObjectId(doc_id)},
        {'$set': {'hidden': True}}
    )

    return redirect(url_for('admin_dashboard'))
@app.route('/admin/unhide-pdf/<doc_id>')
def unhide_pdf(doc_id):

    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))
    docs_col.update_one(
        {'_id': ObjectId(doc_id)},
        {'$set': {'hidden': False}}
    )

    return redirect(url_for('admin_dashboard'))


# ==========================================
# ML recommendation Logic
# ==========================================
def get_recommendations(user):
    user_id = str(user['_id'])
    user_branch = user.get('branch', '')
    user_year = user.get('year', '')
    
    all_docs = list(docs_col.find({}))
    if not all_docs:
        return []
        
    # Get user's download history to perform content-based filtering
    user_dls = list(downloads_col.find({'user_id': user_id}))
    downloaded_doc_ids = {dl['document_id'] for dl in user_dls}
    
    # Generate content-based scores
    # If user has download history, build a user profile text
    user_profile_text = ""
    downloaded_docs = []
    if downloaded_doc_ids:
        downloaded_docs = list(docs_col.find({'_id': {'$in': [ObjectId(id_) for id_ in downloaded_doc_ids]}}))
        user_profile_text = " ".join([f"{d['title']} {d['description']} {d['subject']}" for d in downloaded_docs])
    
    recommendations = []
    
    # Standard TF-IDF logic if user has downloaded documents
    if user_profile_text:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            
            # Extract texts of all candidate documents (not already downloaded by user)
            candidates = [d for d in all_docs if str(d['_id']) not in downloaded_doc_ids]
            
            if candidates:
                cand_texts = [f"{d['title']} {d['description']} {d['subject']}" for d in candidates]
                
                # Fit Vectorizer on candidates + user profile text
                vectorizer = TfidfVectorizer(stop_words='english')
                tfidf_matrix = vectorizer.fit_transform(cand_texts + [user_profile_text])
                
                # The last row is the user profile
                cand_vectors = tfidf_matrix[:-1]
                user_vector = tfidf_matrix[-1]
                
                # Compute Cosine Similarity
                sim_scores = cosine_similarity(cand_vectors, user_vector).flatten()
                
                for idx, doc in enumerate(candidates):
                    # Combine TF-IDF similarity with metadata match
                    meta_score = 0
                    if doc.get('branch') == user_branch:
                        meta_score += 0.4
                    if doc.get('year') == user_year:
                        meta_score += 0.3
                        
                    content_score = sim_scores[idx] # between 0 and 1
                    
                    # Final hybrid score: 70% metadata, 30% content similarity
                    final_score = (meta_score * 0.7) + (content_score * 0.3)
                    final_percentage = min(99, int(final_score * 100))
                    
                    # Ensure some similarity baseline if matching metadata
                    if final_percentage < 40 and (doc.get('branch') == user_branch or doc.get('year') == user_year):
                        final_percentage = 40 + (10 if doc.get('branch') == user_branch else 0) + (10 if doc.get('year') == user_year else 0)
                    
                    recommendations.append({
                        'id': str(doc['_id']),
                        'title': doc['title'],
                        'similarity': final_percentage
                    })
        except Exception as e:
            print(f"[RECS ERROR] Failed TF-IDF recommendation fallback to rule-based: {e}")
            user_profile_text = "" # Fallback to rule-based

    # Rule-based fallback (if no download history, or sklearn error)
    if not user_profile_text:
        # Candidate documents (not downloaded)
        candidates = [d for d in all_docs if str(d['_id']) not in downloaded_doc_ids]
        for doc in candidates:
            score = 0
            if doc.get('branch') == user_branch:
                score += 55
            if doc.get('year') == user_year:
                score += 30
            # Add small random factor to give variety
            score += random.randint(0, 10)
            
            final_percentage = min(99, max(20, score))
            recommendations.append({
                'id': str(doc['_id']),
                'title': doc['title'],
                'similarity': final_percentage
            })
            
    # Sort recommendations by similarity descending, limit to 4
    recommendations.sort(key=lambda x: x['similarity'], reverse=True)
    return recommendations[:4]
@app.route('/my-uploads')
def my_uploads():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    uploads = list(
        docs_col.find(
            {
                "uploader_id": session['user_id']
            }
        ).sort("upload_date", -1)
    )

    return render_template(
        "my_uploads.html",
        uploads=uploads
    )
@app.route('/delete-upload/<doc_id>', methods=['POST'])
def delete_upload(doc_id):

    if 'user_id' not in session:
        return jsonify({
            "success": False,
            "message": "Unauthorized"
        }), 401

    try:

        doc = docs_col.find_one({
            "_id": ObjectId(doc_id),
            "uploader_id": session['user_id']
        })

        if not doc:
            return jsonify({
                "success": False,
                "message": "File not found"
            })

        # Delete PDF file
        filepath = os.path.join(
            app.config['UPLOAD_FOLDER'],
            doc['filename']
        )

        if os.path.exists(filepath):
            os.remove(filepath)

        # Delete download history
        downloads_col.delete_many({
            "document_id": str(doc['_id'])
        })

        # Delete MongoDB document
        docs_col.delete_one({
            "_id": ObjectId(doc_id)
        })

        return jsonify({
            "success": True,
            "message": "PDF deleted successfully."
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        })
@app.route('/files/<filename>')
def serve_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
@app.route('/preview/<doc_id>')
def preview_pdf(doc_id):

    if 'user_id' not in session:
        return redirect(url_for('login'))

    doc = docs_col.find_one({"_id": ObjectId(doc_id)})
    if not doc:
        return "File Not Found", 404

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], doc['filename'])

    if not os.path.exists(file_path):
        return "File missing in server uploads folder", 404

    ext = doc['filename'].rsplit('.', 1)[1].lower()

    # ✅ PDF → OPEN IN BROWSER (NOT DOWNLOAD)
    if ext == "pdf":
        return send_from_directory(
            app.config['UPLOAD_FOLDER'],
            doc['filename'],
            as_attachment=False,   # 🔥 THIS IS THE FIX
            mimetype='application/pdf'
        )

    # ✅ DOC / DOCX → STILL OPEN INLINE (browser dependent)
    elif ext in ["doc", "docx"]:
        return send_from_directory(
            app.config['UPLOAD_FOLDER'],
            doc['filename'],
            as_attachment=False
        )

    return "Unsupported file type", 400
# ==========================================
# Authentication & OTP Endpoints
# ==========================================
@app.route('/api/send-otp', methods=['POST'])
def send_otp():
    data = request.get_json() or {}
    email = data.get('email')
    
    if not email:
        return jsonify({'success': False, 'error': 'Email is required'}), 400
        
    # Generate 6-digit OTP
    otp = "".join(random.choices(string.digits, k=6))
    
    try:
        # Store in Mongo OTPs collection. Note: created_at has TTL index, automatically handles expiration
        otps_col.delete_many({'email': email}) # Clear any previous active OTPs
        otps_col.insert_one({
            'email': email,
            'otp': otp,
            'created_at': datetime.now(timezone.utc)
        })
            #Send Email
        sent = send_email_otp(email, otp)
        if sent:
            return jsonify({'success': True, 'message': 'OTP sent successfully to your email.'})
        else:
            return jsonify({'success': False, 'error': 'Failed to send OTP email. Please ensure SMTP credentials are correct in the server .env file.'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': f"Database error: {str(e)}"}), 500
@app.route('/api/send-reset-otp', methods=['POST'])
def send_reset_otp():

    data = request.get_json() or {}
    email = data.get('email')

    if not email:
        return jsonify({'success': False, 'error': 'Email is required'}), 400

    user = users_col.find_one({'email': email})

    if not user:
        return jsonify({'success': False, 'error': 'Email not registered'}), 400

    otp = "".join(random.choices(string.digits, k=6))

    otps_col.delete_many({'email': email})

    otps_col.insert_one({
        'email': email,
        'otp': otp,
        'created_at': datetime.now(timezone.utc)
    })

    if send_email_otp(email, otp):
        return jsonify({
            'success': True,
            'message': 'OTP sent successfully.'
        })

    return jsonify({
        'success': False,
        'error': 'Failed to send OTP.'
    }), 500
@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json() or {}
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    branch = data.get('branch')
    year = data.get('year')
    otp = data.get('otp')
    
    if not all([name, email, password, branch, year, otp]):
        return jsonify({'success': False, 'error': 'All fields are required'}), 400
        
    # Check if user already exists
    if users_col.find_one({'email': email}):
        return jsonify({'success': False, 'error': 'Email is already registered'}), 400
        
    # Verify OTP
    otp_record = otps_col.find_one({'email': email})
    if not otp_record:
        return jsonify({'success': False, 'error': 'OTP expired or not requested.'}), 400
        
    if otp_record['otp'] != otp:
        return jsonify({'success': False, 'error': 'Invalid OTP.'}), 400
        
    try:
        # Hash password and insert user
        pwd_hash = generate_password_hash(password)
        user_id = users_col.insert_one({
            'name': name,
            'email': email,
            'password_hash': pwd_hash,
            'branch': branch,
            'year': year
        }).inserted_id
        
        # Clean up verified OTP
        otps_col.delete_many({'email': email})
        
        return jsonify({'success': True, 'message': 'Registration successful!'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Registration failed: {str(e)}'}), 500
@app.route('/api/login', methods=['POST'])
def api_login():

    data = request.get_json() or {}

    email = data.get('email')
    password = data.get('password')
    role = data.get('role')

    if not email or not password or not role:
        return jsonify({
            "success": False,
            "error": "Please enter Email, Password and select Login Type."
        }), 400

    user = users_col.find_one({"email": email})

    if not user:
        return jsonify({
            "success": False,
            "error": "Invalid Email."
        }), 401

    if not check_password_hash(user["password_hash"], password):
        return jsonify({
            "success": False,
            "error": "Invalid Password."
        }), 401

    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "studyhub4436@gmail.com")

    # -----------------------------
    # ADMIN LOGIN
    # -----------------------------
    if role == "admin":

        if email != ADMIN_EMAIL:
            return jsonify({
                "success": False,
                "error": "This account is not an Admin."
            }), 403

        session["user_id"] = str(user["_id"])
        session["role"] = "admin"

        return jsonify({
            "success": True,
            "role": "admin",
            "message": "Admin Login Successful"
        })

    # -----------------------------
    # USER LOGIN
    # -----------------------------
    if role == "user":

        if email == ADMIN_EMAIL:
            return jsonify({
                "success": False,
                "error": "Please login as Admin."
            }), 403

        session["user_id"] = str(user["_id"])
        session["role"] = "user"

        return jsonify({
            "success": True,
            "role": "user",
            "message": "User Login Successful"
        })

    return jsonify({
        "success": False,
        "error": "Invalid Login Type."
    }), 400

@app.route('/api/reset-password', methods=['POST'])
def reset_password():

    data = request.get_json() or {}

    email = data.get("email")
    otp = data.get("otp")
    password = data.get("password")

    otp_record = otps_col.find_one({'email': email})

    if not otp_record:
        return jsonify({
            'success': False,
            'error': 'OTP expired'
        }), 400

    if otp_record['otp'] != otp:
        return jsonify({
            'success': False,
            'error': 'Invalid OTP'
        }), 400

    users_col.update_one(
        {'email': email},
        {
            '$set': {
                'password_hash': generate_password_hash(password)
            }
        }
    )

    otps_col.delete_many({'email': email})

    return jsonify({
        'success': True,
        'message': 'Password updated successfully'
    })
@app.route('/logout')
def logout_route():
    session.clear()
    return redirect(url_for('login'))

# ==========================================
# Dashboard APIs
# ==========================================
@app.route('/api/profile/update', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
    data = request.get_json() or {}
    name = data.get('name')
    email = data.get('email')
    branch = data.get('branch')
    year = data.get('year')
    
    if not name or not email:
        return jsonify({'success': False, 'error': 'Name and Email are required'}), 400
        
    try:
        # Check if email is being updated and is already taken by another user
        existing_user = users_col.find_one({'email': email})
        if existing_user and str(existing_user['_id']) != session['user_id']:
            return jsonify({'success': False, 'error': 'Email is already taken by another user'}), 400
            
        users_col.update_one(
            {'_id': ObjectId(session['user_id'])},
            {'$set': {
                'name': name,
                'email': email,
                'branch': branch,
                'year': year
            }}
        )
        return jsonify({'success': True, 'message': 'Profile updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to update profile: {str(e)}'}), 500

@app.route('/api/upload', methods=['POST'])
def api_upload():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
    title = request.form.get('title')
    description = request.form.get('description')
    branch = request.form.get('branch')
    year = request.form.get('year')
    subject = request.form.get('subject')
    file = request.files.get('file')
    
    if not all([title, description, branch, year, subject, file]):
        return jsonify({'success': False, 'error': 'All fields and file are required'}), 400
        
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    if not allowed_file(file.filename):
        return jsonify({
        'success': False,
        'error': 'Only PDF & DOCS files are allowed.'
    }), 400

    #Secure filename and add timestamp prefix to avoid collisions
    orig_name = secure_filename(file.filename)
    unique_prefix = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')
    filename = f"{unique_prefix}_{orig_name}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        file.save(filepath)
        
        # Save document metadata in MongoDB
        docs_col.insert_one({
            'title': title,
            'description': description,
            'branch': branch,
            'year': year,
            'subject': subject,
            'filename': filename,
            'downloads_count': 0,
            'hidden':False,
            'uploader_id': session['user_id'],
            'upload_date': datetime.now(timezone.utc)
        })
        
        # Get uploaded file extension
        file_ext = file.filename.rsplit('.', 1)[1].lower()

        if file_ext == "pdf":
            message = "PDF uploaded successfully."
        else:
            message = "Document uploaded successfully."

        return jsonify({
            'success': True,
            'message': message
        })
    except Exception as e:
        return jsonify({
        'success': False,
        'error': f'File upload failed: {str(e)}'
    }), 500
    

@app.route('/api/search', methods=['GET'])
def api_search():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
    query = request.args.get('q', '').strip()
    branch = request.args.get('branch', '').strip()
    year = request.args.get('year', '').strip()
    
    # Query MongoDB for filters (branch / year)
    filters = {
        'hidden':{'$ne':True}
    }
    if branch and branch != "Select Branch" and branch != "Choose Branch":
        filters['branch'] = branch
    if year and year != "Select Year" and year != "Choose Year":
        filters['year'] = year
        
    all_filtered_docs = list(docs_col.find(filters))
    
    if not all_filtered_docs:
        return jsonify([])
        
    # NLP Search using TF-IDF & Cosine Similarity
    if query:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            
            doc_texts = [f"{d['title']} {d['description']} {d['subject']}" for d in all_filtered_docs]
            
            vectorizer = TfidfVectorizer(stop_words='english')
            tfidf_matrix = vectorizer.fit_transform(doc_texts)
            query_vector = vectorizer.transform([query])
            
            sim_scores = cosine_similarity(tfidf_matrix, query_vector).flatten()
            
            results = []
            for idx, doc in enumerate(all_filtered_docs):
                score = sim_scores[idx]
                # Include document details + similarity score
                results.append({
                    'id': str(doc['_id']),
                    'title': doc['title'],
                    'branch': doc['branch'],
                    'year': doc['year'],
                    'subject': doc['subject'],
                    'downloads': doc.get('downloads_count', 0),
                    'score': float(score)
                })
                
            # Sort by similarity score descending
            results.sort(key=lambda x: x['score'], reverse=True)
            # Remove score key before returning or keep it for debugging
            return jsonify(results)
        except Exception as e:
            print(f"[SEARCH ERROR] NLP Search failed, falling back to substring match: {e}")
            # Fallback to simple title/description substring match
            results = []
            for doc in all_filtered_docs:
                if query.lower() in doc['title'].lower() or query.lower() in doc['description'].lower() or query.lower() in doc['subject'].lower():
                    results.append({
                        'id': str(doc['_id']),
                        'title': doc['title'],
                        'branch': doc['branch'],
                        'year': doc['year'],
                        'subject': doc['subject'],
                        'downloads': doc.get('downloads_count', 0)
                    })
            return jsonify(results)
    else:
        # No search query, just return list filtered by branch/year
        results = []
        for doc in all_filtered_docs:
            results.append({
                'id': str(doc['_id']),
                'title': doc['title'],
                'branch': doc['branch'],
                'year': doc['year'],
                'subject': doc['subject'],
                'downloads': doc.get('downloads_count', 0)
            })
        return jsonify(results)

@app.route('/api/download/<doc_id>')
def api_download(doc_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        doc = docs_col.find_one({'_id': ObjectId(doc_id)})

        if not doc:
            return "File not found", 404

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], doc['filename'])

        if not os.path.exists(file_path):
            return "File not found in server", 404

        downloads_col.insert_one({
            'user_id': session['user_id'],
            'document_id': doc_id,
            'download_date': datetime.now(timezone.utc)
        })

        docs_col.update_one(
            {'_id': ObjectId(doc_id)},
            {'$inc': {'downloads_count': 1}}
        )

        return send_from_directory(
            app.config['UPLOAD_FOLDER'],
            doc['filename'],
            as_attachment=True,
            download_name=doc['title']
        )

    except Exception as e:
        return f"Download failed: {str(e)}", 500
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)