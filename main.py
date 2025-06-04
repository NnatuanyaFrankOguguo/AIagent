from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from oauth_router import router as auth_router
from calendar_router import router as prompt_router
from db_config import engine
from sqlalchemy.exc import OperationalError
from model import Base

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Or ["*"] for all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(auth_router, prefix="/oauth", tags=["OAuth"])
app.include_router(prompt_router, prefix="/prompt", tags=["Prompt"])

try:
    with engine.connect() as connection:
        # Test the connection to the database
        print("✅ Database connected successfully!")
except OperationalError as e:
    print(f"❌ Database connection failed: {e}")
    raise RuntimeError("Database connection failed. Please check your configuration.")

Base.metadata.create_all(bind=engine)