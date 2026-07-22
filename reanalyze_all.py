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
docs = list(docs_col.find({}))
for doc in docs:
    filepath = os.path.join(UPLOAD_FOLDER, doc['filename'])
    if os.path.exists(filepath):
        print(f"Analyzing: {doc.get('title')} (Subject: {doc.get('subject')})...")
        ai_analysis = analyze_pdf_with_ai(filepath, doc.get('title'), doc.get('subject'))
        docs_col.update_one(
            {"_id": doc["_id"]},
            {"$set": {"ai_analysis": ai_analysis}}
        )
        print(f" -> Score: {ai_analysis.get('score')} | Reason: {ai_analysis.get('reason')}")
    else:
        print(f" -> File not found: {filepath}")

print("Recalculating recommendation stars...")
recalculate_all_recommendations()
print("Done! All PDFs have been re-analyzed and recommendation stars updated.")
