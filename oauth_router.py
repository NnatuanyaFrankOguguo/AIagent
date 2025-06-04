from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Response, Depends, Cookie, APIRouter
from fastapi.responses import RedirectResponse, JSONResponse
import httpx
import secrets
import os
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from crud import get_db, create_user
from loggerInfo import logger

router = APIRouter()

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8000/oauth/callback"
SCOPES = "https://www.googleapis.com/auth/calendar.events https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/userinfo.email"

# Simple in-memory storage of state and tokens by user_id (for demo only)
# state_store = {}
# user_tokens = {}

# In-memory "DB" for demo purposes (use real DB in production)
user_sessions = {}  # session_id -> user info & tokens

def generate_session_id():
    return secrets.token_urlsafe(16)


async def refresh_access_token(refresh_token: str ) -> dict:
    """Refresh the access token using the refresh token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            },
        )
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Failed to refresh access token {response.text}")
        return response.json()

async def get_valid_access_token(session_id: str) -> str:
    """Return a valid access token for a session, refreshing if expired."""
    session = user_sessions.get(session_id)
    if not session:
        logger.error("[TOKEN] Session not found")
        raise HTTPException(status_code=401, detail="Session not found")
    
    expires_at = session.get("expires_at")
    now = datetime.utcnow()

     # Add default expiry time if not present (fallback)
    if expires_at is None:
        expires_at = now + timedelta(seconds=3600)

    if  now >= expires_at:
        logger.info(f"[TOKEN] Expired. Refreshing token for session: {session_id}")
        # Token expired or no expiry info — refresh
        token_data = await refresh_access_token(session["refresh_token"])
        session["access_token"] = token_data["access_token"]
        expires_in = token_data.get("expires_in", 3600)
        session["expires_at"] = now + timedelta(seconds=expires_in)
        user_sessions[session_id] = session # Update session store
        logger.info(f"\033[0;32m[TOKEN REFRESHED]\033[0m New access token for session {session_id}")
    return session["access_token"]

#User initiates login via Google
@router.get("/login")
async def login():
    # Generate a unique state parameter to prevent CSRF attacks
    state = secrets.token_urlsafe(16)
    # state_store[state] = {"user_id": user_id, "expires_at": datetime.utcnow() + timedelta(minutes=10)}
    oauth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={CLIENT_ID}&"
        f"response_type=code&"
        f"scope={SCOPES}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"state={state}&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    logger.info(f"\033[0;33m[LOGIN INITIATED]\033[0m Generating OAuth URL with state: {state}")
    response = RedirectResponse(oauth_url)
    
    # Store state in a cookie for validation later
    response.set_cookie(key="oauth_state", value=state, httponly=True)
    return response
# Sends the user to Google and stores state in a secure cookie.

# User is redirected back to this endpoint after Google OAuth flow 
@router.get("/callback") #Handles the redirect back from Google with code and state
async def oauth_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, oauth_state: Optional[str] = Cookie(None), db: AsyncSession = Depends(get_db)):
    if code is None or state is None:
        logger.error("[CALLBACK] Missing code or state in request")
        raise HTTPException(status_code=400, detail="Missing code or state parameter")
    
    # Validate state
    if state != oauth_state:
        logger.error("[CALLBACK] State mismatch – Possible CSRF attack")
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    logger.info(f"\033[0;33m[CALLBACK]\033[0m Received code and valid state, requesting tokens...")
    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )

    if token_response.status_code != 200:
        logger.error(f"[CALLBACK] Failed to exchange code for tokens: {token_response.text}")
        raise HTTPException(status_code=400, detail=f"Failed to exchange code for tokens: {token_response.text}")
    

    token_data = token_response.json()
    logger.info("\033[0;32m[TOKEN SUCCESS]\033[0m Received access and refresh tokens")
    if "access_token" not in token_data or "refresh_token" not in token_data:
        raise HTTPException(status_code=400, detail=f"Failed to get tokens: {token_data}")
    
   
    # step 1: Get user info from Google
    async with httpx.AsyncClient() as client:
        user_info_response = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"}
        )
    

    if user_info_response.status_code != 200:
        logger.error(f"[CALLBACK] Failed to get user info: {user_info_response.text}")
        raise HTTPException(status_code=400, detail=f"Failed to get user info: {user_info_response.text}")
    # step 2: Parse user info
    
    user_info = user_info_response.json()
    logger.info(f"\033[0;32m[USER INFO]\033[0m Email: {user_info.get('email')} | Sub: {user_info.get('sub')}")

    #step 2: Create or update user in the database

    try:
        await create_user(db, user_info, token_data)
        logger.info(f"\033[0;32m[DB]\033[0m User created or updated in database")
    except Exception as e:
        logger.error(f"[DB ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    # step 3: Create a session for the user
    expires_in = token_data.get("expires_in", 3600)
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    session_id = generate_session_id()
    user_sessions[session_id] = {
        "access_token": token_data["access_token"],
        "refresh_token": token_data["refresh_token"],
        "expires_at": expires_at,
        "user_info": user_info,  # Store user info for later use
    }
    logger.info(f"\033[0;36m[SESSION CREATED]\033[0m ID: {session_id} | Expires: {expires_at}")

    # step 4: Redirect user to the chatbot interface
    response = RedirectResponse(url="http://localhost:3000/chat")  # Or your deployed chatbot URL
    session_lifetime = timedelta(days=7)
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        max_age=session_lifetime.total_seconds(),
        expires=session_lifetime.total_seconds(),
        samesite="Lax",
        secure=not os.getenv("ENV") == "development"  # Use False during local development if needed
    )
    logger.info(f"\033[0;36m[COOKIE SET]\033[0m Secure: {not os.getenv('ENV') == 'development'} | Session ID: {session_id}")
    return response

    # WHAT I DID BEFORE 
    # # Calculate token expiry
    # expires_in = token_data.get("expires_in", 3600)
    # expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

    # # Create a session for the user
    # session_id = generate_session_id()
    # user_sessions[session_id] = {
    #     "access_token": token_data["access_token"],
    #     "refresh_token": token_data["refresh_token"],
    #     "expires_at": expires_at,
    # }

    # response = RedirectResponse(url="http://localhost:3000/chat") # Or your deployed chatbot URL
    # # Set session cookie for user
    # session_lifetime = timedelta(days=7)
    # response.set_cookie(key="session_id", value=session_id, httponly=True
    #                     , max_age=session_lifetime.total_seconds(), expires=session_lifetime.total_seconds(),
    #                     samesite="Lax", secure=True)  # Use secure=True in production
    # return response

async def get_session_id(session_id: Optional[str] = Cookie(None)):
    """Get session ID from cookie, raise 401 if not found."""
    if not session_id or session_id not in user_sessions:
        logger.warning("[GET /me] Invalid or missing session ID")
        raise HTTPException(status_code=401, detail="Unauthorized")
    return session_id

@router.get("/me")
async def get_me(session_id: str = Cookie(None)):
    """Returns basic session info to the frontend."""
    if not session_id or session_id not in user_sessions:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    session = user_sessions[session_id]
    logger.info(f"\033[0;36m[GET /me]\033[0m Session Valid. Email: {session['user_info'].get('email')}")
    return {
        "session_id": session_id,
        "expires_at": session["expires_at"],
        "email": session["user_info"].get("email"),
        "name": session["user_info"].get("name"),
        "picture": session["user_info"].get("picture"),
        #"access_token": session["access_token"],  # Optional: remove in production
    }

@router.get("/logout")
async def logout(session_id: Optional[str] = Cookie(None)):
    if session_id and session_id in user_sessions:
        del user_sessions[session_id]
        logger.info(f"\033[0;33m[LOGOUT]\033[0m Session {session_id} cleared")
    response = JSONResponse(content={"message": "Logged out"})
    response.delete_cookie("session_id")
    return response

