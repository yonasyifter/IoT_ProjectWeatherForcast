import firebase_admin
from firebase_admin import credentials, auth, firestore
import os
from dotenv import load_dotenv

load_dotenv()


def init_firebase():
    if len(firebase_admin._apps) > 0:
        print("(DATABASE) Firebase Admin SDK already initialized.")
        return
    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    print(f"(DATABASE) Initial cred_path from ENV: {cred_path}")
    
    # Handle Docker environment where absolute Windows paths in .env won't work
    if cred_path:
        # Strip quotes if present
        cred_path = cred_path.strip('"').strip("'")
        
        if not os.path.exists(cred_path):
            print(f"(DATABASE) Path {cred_path} does not exist. Searching...")
            filename = os.path.basename(cred_path)
            # Check common locations in Docker
            search_paths = [
                filename,
                os.path.join("/app", filename),
                os.path.join("/app/backend", filename),
                os.path.join(os.path.dirname(__file__), "..", filename),
                os.path.join(os.path.dirname(__file__), "..", "..", filename),
                "/app/iot-project-49099-firebase-adminsdk-fbsvc-e448ec3df1.json"
            ]
            for p in search_paths:
                print(f"(DATABASE) Checking: {p}")
                if os.path.exists(p):
                    print(f"(DATABASE) Found credentials at: {p}")
                    cred_path = p
                    break
    
    print(f"(DATABASE) Final cred_path used: {cred_path}")
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)


def get_firebase_auth():
    """Get Firebase Auth instance"""
    init_firebase()
    return auth


def get_firestore_db():
    """Get Firestore instance"""
    init_firebase()
    return firestore.client()


def create_db():
    """Firebase initialization - collections are created on first write"""
    init_firebase()
