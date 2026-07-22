import os
import sys
from pymongo import MongoClient
from dotenv import load_dotenv

# Ensure we can import app
sys.path.append(os.getcwd())

load_dotenv()
MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'studyhub')
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY or "..." in GEMINI_API_KEY or GEMINI_API_KEY == "your_api_key":
    print("Error: Please set a valid GEMINI_API_KEY in your .env file first!")
    print("Currently it is set to a placeholder: ", GEMINI_API_KEY)
    sys.exit(1)

import google.generativeai as genai
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]
docs_col = db['documents']

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')

from app import analyze_pdf_with_ai, recalculate_all_recommendations

print("Starting re-analysis of all PDFs using Gemini...")
import re
import fitz

# Process chronologically so we build recommendations incrementally
docs = list(docs_col.find({}).sort("_id", 1))
for doc in docs:
    filepath = os.path.join(UPLOAD_FOLDER, doc['filename'])
    if os.path.exists(filepath):
        subject = doc.get('subject', '')
        
        # Find the current recommended best document for this subject BEFORE analyzing the new one
        current_best_doc = docs_col.find_one({
            "subject": {"$regex": f"^{re.escape(subject.strip())}$", "$options": "i"},
            "is_ai_recommended": True
        })
        
        # Avoid comparing the document to itself
        if current_best_doc and current_best_doc["_id"] == doc["_id"]:
            current_best_doc = None

        current_best_text = None
        current_best_score = 0
        if current_best_doc:
            current_best_score = current_best_doc.get("ai_analysis", {}).get("score", 0)
            best_filepath = os.path.join(UPLOAD_FOLDER, current_best_doc['filename'])
            if os.path.exists(best_filepath):
                try:
                    fitz_doc = fitz.open(best_filepath)
                    best_text = ""
                    for page in fitz_doc:
                        best_text += page.get_text()
                    fitz_doc.close()
                    current_best_text = best_text[:15000]
                except Exception as best_err:
                    print("Error reading current best PDF text:", best_err)

        print(f"Analyzing: {doc.get('title')} (Subject: {doc.get('subject')})...")
        ai_analysis = analyze_pdf_with_ai(filepath, doc.get('title'), doc.get('subject'), current_best_text, current_best_score)
        docs_col.update_one(
            {"_id": doc["_id"]},
            {"$set": {"ai_analysis": ai_analysis}}
        )
        print(f" -> Score: {ai_analysis.get('score')} | Reason: {ai_analysis.get('reason')}")
        
        # Update the best badge immediately so the next doc compares against the latest winner
        recalculate_all_recommendations()
    else:
        print(f" -> File not found: {filepath}")

print("Recalculating final recommendation stars...")
recalculate_all_recommendations()
print("Done! All PDFs have been re-analyzed and recommendation stars updated.")
