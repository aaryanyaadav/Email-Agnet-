from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Groq Settings
    GROQ_API_KEY: str = "mock_key_for_dev"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Google OAuth Settings
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8080/"
    GOOGLE_CREDENTIALS_FILE: str = "credentials.json"
    GOOGLE_TOKEN_FILE: str = "token.json"

    # Database
    DATABASE_URL: str = "sqlite:///./placement_agent.db"

    # Scheduler & System Behavior
    CHECK_INTERVAL: int = 300  # seconds (5 minutes)
    ENABLE_DRY_RUN: bool = False
    LOG_LEVEL: str = "INFO"

    # Base Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
