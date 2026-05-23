import os
import time
import concurrent.futures
from datetime import datetime, timedelta

import requests
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Security, status
from fastapi.security import HTTPBearer, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from firebase_admin import auth as firebase_auth
from pydantic import BaseModel

from app.database import get_firestore_db, init_firebase
from app.models import UserLoginRequest, UserRegisterRequest


router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()

# OAuth2 scheme for Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

# Firebase-only configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "session")
SESSION_EXPIRE_DAYS = int(os.getenv("SESSION_EXPIRE_DAYS", "5"))
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
FIRESTORE_AUTH_TIMEOUT_SECONDS = float(os.getenv("FIRESTORE_AUTH_TIMEOUT_SECONDS", "5"))
FIRESTORE_AUTH_REQUIRED = os.getenv("FIRESTORE_AUTH_REQUIRED", "false").lower() == "true"


def get_db():
    return get_firestore_db()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_role: str


class MessageResponse(BaseModel):
    message: str


class RegisterResponse(BaseModel):
    uid: str
    email: str
    message: str


class SessionLoginRequest(BaseModel):
    id_token: str


class SessionStatusResponse(BaseModel):
    uid: str
    email: str
    role: str


def _get_admin_user(uid: str, decoded_token: dict | None = None) -> dict:
    print(f"[AUTH] Fetching Firestore user doc for UID: {uid}")
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(lambda: get_db().collection("users").document(uid).get())

    try:
        user_doc = future.result(timeout=FIRESTORE_AUTH_TIMEOUT_SECONDS)
    except Exception as exc:
        future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)
        print(f"[AUTH] Firestore lookup unavailable for UID {uid}: {type(exc).__name__}: {exc}")

        if FIRESTORE_AUTH_REQUIRED:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Firestore user-role lookup is unavailable. Check Firebase service account credentials.",
            ) from exc

        decoded_token = decoded_token or {}
        return {
            "uid": uid,
            "role": decoded_token.get("role") or decoded_token.get("admin_role") or "visitor",
            "email": decoded_token.get("email", ""),
        }
    else:
        executor.shutdown(wait=False, cancel_futures=True)

    if not user_doc.exists:
        print(f"[AUTH] ERROR: No Firestore document found for UID: {uid}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"User {uid} not found in Firestore 'users' collection. "
                   "Create the document with role: admin or visitor.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_data = user_doc.to_dict()
    role = user_data.get("role", "")
    email = user_data.get("email", "")
    print(f"[AUTH] Firestore doc found — email={email}, role={role!r}, keys={list(user_data.keys())}")

    if role not in ["admin", "visitor"]:
        print(f"[AUTH] ERROR: role {role!r} not in ['admin','visitor']")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{role}' is not permitted. Firestore doc for {uid} must have role: admin or visitor.",
        )

    print(f"[AUTH] Access granted — uid={uid} role={role}")
    return {
        "uid": uid,
        "role": role,
        "email": email,
    }


def get_firebase_admin_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    FIREBASE ADMIN ONLY AUTHENTICATION
    Validates Firebase ID token and enforces admin role from Firestore.

    Used as a dependency for all admin-protected endpoints.
    """
    try:
        init_firebase()
        # Verify Firebase ID token
        decoded_token = firebase_auth.verify_id_token(token)
        uid = decoded_token.get("uid")

        return _get_admin_user(uid, decoded_token)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def get_admin_session_user(request: Request) -> dict:
    """Verify user from Authorization Bearer token."""
    init_firebase()
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header[7:].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Step 1: verify Firebase ID token
    try:
        decoded_token = firebase_auth.verify_id_token(token)
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase token expired — please log in again",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except firebase_auth.InvalidIdTokenError as e:
        print(f"[AUTH] Invalid token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Firebase token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        print(f"[AUTH] Token verification error: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {type(e).__name__}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Step 2: look up user in Firestore — let HTTPException propagate as-is
    uid = decoded_token.get("uid")
    print(f"[AUTH] Token OK for UID: {uid}")
    return _get_admin_user(uid, decoded_token)


# Shared login logic to avoid code duplication
def _authenticate_firebase_user(email: str, password: str) -> TokenResponse:
    """
    Shared Firebase authentication logic.
    Verifies credentials and enforces admin role.
    """
    try:
        user = firebase_auth.get_user_by_email(email)
        uid = user.uid

        # Verify password using Firebase REST API
        api_key = os.getenv("FIREBASE_API_KEY")

        response = requests.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}",
            json={
                "email": email,
                "password": password,
                "returnSecureToken": True
            },
            timeout=10
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        data = response.json()
        access_token = data.get("idToken")

        # Get user role from Firestore and ENFORCE admin role
        user_doc = get_db().collection("users").document(uid).get()

        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not found in admin database"
            )

        user_data = user_doc.to_dict()
        user_role = user_data.get("role", "visitor")

        # Strict admin enforcement
        if user_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Firebase admin users can access this API. Your account does not have admin privileges."
            )

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user_role=user_role
        )

    except HTTPException:
        raise
    except firebase_auth.UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase email not registered"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {str(e)}"
        ) from e


@router.post("/login/firebase", response_model=TokenResponse)
def login_firebase(req: UserLoginRequest):
    """
    Firebase Admin Login Endpoint (JSON)

    Login with Firebase email and password. User MUST have admin role in Firestore.
    Returns access token to use in protected endpoints.

    Steps:
    1. Enter your Firebase admin email and password
    2. You'll receive an access_token
    3. Use this token as: Authorization: Bearer <access_token>
    4. All protected endpoints will validate your admin role in Firebase
    """
    return _authenticate_firebase_user(req.email, req.password)


@router.get("/session-status", response_model=SessionStatusResponse)
def session_status(request: Request):
    """Get current user info from Bearer token."""
    admin_user = get_admin_session_user(request)
    return SessionStatusResponse(
        uid=admin_user["uid"],
        email=admin_user.get("email", ""),
        role=admin_user["role"],
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(req: UserRegisterRequest):
    """
    Firebase User Registration Endpoint

    Register a new user account in Firebase.

    - **email**: User's email (must be unique)
    - **password**: Password (minimum 6 characters)

    Steps:
    1. Provide email and password. Display name will be derived automatically from email.
    2. User will be created in Firebase Authentication
    3. User profile stored in Firestore with 'visitor' role
    """
    try:
        # Check if email already exists in Firebase
        try:
            existing_user = firebase_auth.get_user_by_email(req.email)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        except firebase_auth.UserNotFoundError:
            # This is expected - user should not exist
            pass

        user = firebase_auth.create_user(
            email=req.email,
            password=req.password,
            display_name=req.email.split("@")[0]
        )

        # Store user data in Firestore
        db = get_db()
        user_data = {
            "uid": user.uid,
            "email": req.email,
            "display_name": req.email.split("@")[0],
            "role": "visitor",  # Default role for new users
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        db.collection("users").document(user.uid).set(user_data)

        return {
            "uid": user.uid,
            "email": req.email,
            "message": "User registered successfully. You can now login."
        }

    except HTTPException:
        raise
    except firebase_auth.EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/token", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 Login Endpoint for Swagger UI (Form Data)

    This endpoint enables the Swagger UI 'Authorize' button.

    - Enter your Firebase email in the 'username' field
    - Enter your password in the 'password' field
    - User MUST have 'admin' role in Firestore to access protected endpoints

    The token will be automatically used by Swagger UI for all authenticated requests.
    """
    # OAuth2 form uses 'username' field, but we expect email
    return _authenticate_firebase_user(form_data.username, form_data.password)
