from fastapi import APIRouter, Depends, Request, HTTPException, Response, Cookie
import asyncio
from prompt_router import validate_request
from calendar_api import create_calendar_event
from typing import Optional
from oauth_router import user_sessions


router = APIRouter()

async def get_session_id(session_id: Optional[str] = Cookie(None)):
    """Get session ID from cookie, raise 401 if not found."""
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return session_id

async def get_access_token_from_session(session_id: str) -> str:
    session = user_sessions.get(session_id)
    if not session or "access_token" not in session:
        raise HTTPException(status_code=401, detail="Session expired or invalid.")
    
    return session["access_token"]

@router.post("/")
async def prompt_handler(request: Request, response: Response, session_id: str = Depends(get_session_id)):
    """
    Handle the prompt request.
    """
    # Logic to handle the prompt
    body = await request.json()
    user_prompt = body.get("prompt")

    # 1.Use a lightweight LLM or rule-based router (e.g., OpenAI, Llama.cpp)
    try:

        # Step 2: Get access token from session ID
        access_token = await get_access_token_from_session(session_id)
        print(f"==> Access token retrieved: {access_token[:6]}...")

        print("==> Starting validation...")
        # Validate the request using the prompt router
        validation_result = await validate_request(user_prompt, access_token)
        
        print(f"==> successfully created event: {validation_result}")

        # if not validation_result:
        #     print("==> Validation failed or returned False success flag.")
        #     raise HTTPException(status_code=400, detail="Invalid request, this is not a calendar event.")
        
        # # Step 2: Get access token from session ID
        # access_token = await get_access_token_from_session(session_id)
        # print(f"==> Access token retrieved: {access_token[:6]}...")

        
        # print("==> Validation passed. Proceeding to create event...")
        # # 2. If the request is valid, process it
        # create_event = await create_calendar_event( validation_result, access_token)
        
        print(f"==> Event created successfully: {validation_result}")
        # Process the validated request
        # Here you would typically call another service or function to handle the request
        return {"message": "Request processed successfully", "data": validation_result}

    except Exception as e:
        print(f"==> Exception occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

   