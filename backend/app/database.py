import os
import json
import firebase_admin
from firebase_admin import credentials, auth, firestore
from dotenv import load_dotenv

load_dotenv()

def init_firebase():
    if len(firebase_admin._apps) > 0:
        print("(DATABASE) Firebase Admin SDK already initialized.")
        return

    # Try reading as a JSON string first (Production/ECS mode)
    cred_json = os.getenv("FIREBASE_CREDENTIALS")
    if cred_json:
        try:
            print("(DATABASE) Initializing Firebase from JSON string environment variable.")
            cred_dict = json.loads(cred_json.strip('"').strip("'"))
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            return
        except Exception as e:
            print(f"(DATABASE) Error parsing FIREBASE_CREDENTIALS JSON: {e}")

    # Try initializing from individual environment variables
    project_id = os.getenv("FIREBASE_PROJECT_ID")
    private_key = os.getenv("FIREBASE_PRIVATE_KEY")
    client_email = os.getenv("FIREBASE_CLIENT_EMAIL")

    if project_id and private_key and client_email:
        try:
            print("(DATABASE) Initializing Firebase from individual environment variables.")
            # Ensure private key has correct newline characters
            if private_key.startswith('"') and private_key.endswith('"'):
                private_key = private_key[1:-1]
            private_key = private_key.replace('\\n', '\n')

            cred_dict = {
                "type": "service_account",
                "project_id": project_id,
                "private_key": private_key,
                "client_email": client_email,
                "token_uri": "https://oauth2.googleapis.com/token",
            }
            # Add optional fields if present
            pk_id = os.getenv("FIREBASE_PRIVATE_KEY_ID")
            if pk_id:
                cred_dict["private_key_id"] = pk_id
            client_id = os.getenv("FIREBASE_CLIENT_ID")
            if client_id:
                cred_dict["client_id"] = client_id

            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            return
        except Exception as e:
            print(f"(DATABASE) Error initializing Firebase from environment variables: {e}")

    # Fallback to file path (Local development mode)
    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")

    if cred_path:
        cred_path = cred_path.strip('"').strip("'")
        if not os.path.exists(cred_path):
            filename = os.path.basename(cred_path)
            search_paths = [
                filename,
                os.path.join("/app", filename),
                os.path.join("/app/backend", filename),
                os.path.join(os.path.dirname(__file__), "..", filename),
                os.path.join(os.path.dirname(__file__), "..", "..", filename),
            ]
            for p in search_paths:
                if os.path.exists(p):
                    cred_path = p
                    break

        try:
            print(f"(DATABASE) Initializing Firebase from file: {cred_path}")
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            return
        except Exception as e:
            print(f"(DATABASE) Error loading credentials from file {cred_path}: {e}")

    raise ValueError("FIREBASE_CREDENTIALS (JSON) or FIREBASE_CREDENTIALS_PATH not set or invalid.")

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
