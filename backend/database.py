import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# ======================================================
# 🔐 DATABASE CONNECTION CONFIGURATION
# ======================================================
# It will use your Cloud DB if you set an environment variable, 
# otherwise, it safely falls back to your local MongoDB for testing.
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
# Inside database.py, make sure you have something like this:
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["resume_scanner_db"]
collection = db["candidates"]
roles_collection = db["roles"] # ADD THIS LINE

DB_NAME = "careermatch_ai_db"
COLLECTION_NAME = "candidates"

print("[DB] Initializing database connection...")

try:
    # Set a 5-second timeout so it doesn't hang forever if the DB is offline
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    
    # Force a ping to confirm the connection is actually alive
    client.admin.command('ping')
    print("[DB] Connected to MongoDB.")
    
except ConnectionFailure:
    print("[DB] CRITICAL: Failed to connect to MongoDB. Use MONGO_URI or start local MongoDB.")

# Connect to the specific database and collection
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# ======================================================
# 💾 DATA STORAGE FUNCTIONS
# ======================================================
def save_candidate(data: dict):
    """
    Saves the analyzed resume profile securely to the database.
    This tracks the filename, skills, predicted role, and ATS score.
    """
    try:
        result = collection.insert_one(data)
        print(f"[DB] Profile saved with ID: {result.inserted_id}")
        return True
    except Exception as e:
        print(f"[DB] Error: {e}")
        return False