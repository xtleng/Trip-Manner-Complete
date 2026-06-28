from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Feature flags
    USE_MOCK_DATA: bool = True
    # When True, the chat router calls the real EKD-Trip / CrossTrip
    # wrappers and falls back to mock SSE if they raise. When False, it
    # always streams mock data (useful for demo recording).
    USE_REAL_ALGORITHMS: bool = False

    # Algorithm checkpoints (absolute paths). Empty -> wrapper reports unavailable.
    EKDTRIP_CHECKPOINT: str = ""
    CROSSTRIP_CHECKPOINT: str = ""

    # DeepSeek LLM
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"

    # Database (Supabase PostgreSQL)
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/postgres"

    # Security
    SECRET_KEY: str = "tripManner-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    SESSION_EXPIRE_HOURS: int = 24


settings = Settings()
