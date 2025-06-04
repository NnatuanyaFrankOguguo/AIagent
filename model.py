from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, DateTime, ForeignKey
from db_config import Base
from uuid import uuid4
from datetime import datetime
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = 'users'

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    email = Column(Text, unique=True, index=True, nullable=False)
    name = Column(Text, nullable=False)
    google_id = Column(Text, unique=True)
    access_token = Column(Text)
    refresh_token = Column(Text)
    picture = Column(String, nullable=True)  # for Google avatar
    expires_at = Column(TIMESTAMP)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow)
    chats = relationship("Chat", back_populates="user", cascade="all, delete")

class Chat(Base):
    __tablename__ = "chats"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="chats")