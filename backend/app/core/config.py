from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AI ETF 투자 도우미"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Auth
    APP_USERNAME: str = "admin"
    APP_PASSWORD: str = "1234"
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = "sqlite:///./app.db"

    # OpenAI
    OPENAI_API_KEY: str = ""

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = {
        "env_file": Path(__file__).resolve().parent.parent.parent / ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
