import os
import importlib

# Dynamically import pymongo to avoid static-analysis errors when it's not installed
pymongo = None
MongoClient = None
ConnectionFailure = Exception
try:
    pymongo = importlib.import_module("pymongo")
    MongoClient = getattr(pymongo, "MongoClient")
    ConnectionFailure = getattr(importlib.import_module("pymongo.errors"), "ConnectionFailure")
except Exception:
    pymongo = None


# ======================================================
# 🔐 DATABASE CONNECTION CONFIGURATION
# ======================================================
# Uses `MONGO_URI` environment variable or falls back to localhost.
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "resume_scanner_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "candidates")
ROLES_COLLECTION_NAME = os.getenv("ROLES_COLLECTION_NAME", "roles")

client = None
db = None
collection = None
roles_collection = None

print("[DB] Initializing database connection...")

if MongoClient is None:
    print("[DB] pymongo is not installed. Please install dependencies.")
else:
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print("[DB] Connected to MongoDB.")
    except ConnectionFailure:
        print("[DB] CRITICAL: Failed to connect to MongoDB. Use MONGO_URI or start local MongoDB.")

    if client:
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        roles_collection = db[ROLES_COLLECTION_NAME]


# ======================================================
# 💾 DATA STORAGE FUNCTIONS
# ======================================================
def save_candidate(data: dict) -> bool:
    """Save analyzed resume profile to the database.

    Returns True on success, False on failure.
    """
    if collection is None:
        print("[DB] Error: No database collection available.")
        return False

    try:
        result = collection.insert_one(data)
        print(f"[DB] Profile saved with ID: {result.inserted_id}")
        return True
    except Exception as e:
        print(f"[DB] Error: {e}")
        return False