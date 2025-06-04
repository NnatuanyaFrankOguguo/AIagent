# oauth_router.py or login_handler.py
from sqlalchemy.orm import Session
from db_config import SessionLocal
from model import User, Chat
from datetime import datetime, timedelta


def get_db():
    """Get a new database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def create_user(db: Session, user_info: dict, tokens: dict):
    """Create or update user in DB."""
    google_id = user_info.get("google_id")
    email = user_info.get("email")
    name = user_info.get("name")
    picture = user_info.get("picture")
    access_token = tokens["access_token"]
    refresh_token = tokens.get("refresh_token")
    expires_in = tokens.get("expires_in", 3600)

    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

    user = db.query(User).filter(User.google_id == google_id).first()

    if user:
        # Update existing user
        user.access_token = access_token
        user.refresh_token = refresh_token
        user.expires_at = expires_at
    else:
        # Create new user
        user = User(
            google_id=google_id,
            email=email,
            name=name,
            picture=picture,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at
        )
        db.add(user)

    db.commit() 
