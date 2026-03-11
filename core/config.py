from functools import lru_cache
from pathlib import Path
import os
from dotenv import load_dotenv 
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


load_dotenv()

class Settings(BaseSettings):
    app_name: str = "LLM Gateway"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    database_url: str = os.environ.get("DATABASE_URL")
    redis_url: str = os.environ.get("REDIS_URL")
    qdrant_url: str = os.environ.get("QDRANT_URL")
    qdrant_collection: str = os.environ.get("QDRANT_COLLECTION")
    qdrant_api_key: str = os.environ.get("QDRANT_API_KEY")

    jwt_secret: str = os.environ.get("JWT_SECRET")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expires_minutes: int = 60 * 24

    encryption_secret: str = "replace-with-strong-secret"

    default_openai_model: str = "gpt-4o-mini"
    default_gemini_model: str = "gemini-1.5-flash"
    default_claude_model: str = "claude-3-5-sonnet-latest"

    embedding_dimension: int = 128
    max_upload_size_mb: int = 25
    upload_dir: str = "storage/uploads"

    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60

    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5500",
            "http://127.0.0.1:5500",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
