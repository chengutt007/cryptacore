import os
from pydantic import BaseModel, Field
from typing import List
from dotenv import load_dotenv

# Manually load .env
load_dotenv()


class Settings(BaseModel):
    database_url: str = Field(os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./cryptacoreai.db"))
    secret_key: str = Field(os.getenv("SECRET_KEY", "change_me"))
    model_path: str = Field(os.getenv("MODEL_PATH", "../ml/saved_models"))
    environment: str = Field(os.getenv("ENVIRONMENT", "development"))
    cors_origins: List[str] = Field(["http://localhost:5173", "http://localhost:3000"])


settings = Settings()
