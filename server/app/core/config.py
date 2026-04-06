from pydantic_settings import BaseSettings
from typing import List

import redis


class Settings(BaseSettings):
    # ── App ────────────────────────────────────────────────────────────────────
    APP_NAME: str = "AI Meeting Assistant"
    DEBUG: bool = False
    # Defaults are intentionally dev-friendly so the API can start even if you
    # haven't filled every integration key yet.
    SECRET_KEY: str = "CHANGE_ME_dev_secret"  # used for JWT signing
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # ── Database ───────────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./dev.db"
    DATABASE_URL_SYNC: str = "sqlite:///./dev.db"

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://default:gQAAAAAAARr3AAIncDExOGM1MDY4MjViNzY0NjM1YmFhYmFlYWI2YTczZmRmZXAxNzI0Mzk@direct-escargot-72439.upstash.io:6379"

    # ── JWT ───────────────────────────────────────────────────────────────────
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── OAuth2 Providers ──────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    MICROSOFT_TENANT_ID: str = "common"
    MICROSOFT_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/microsoft/callback"

    # ── AI Services ───────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""                 # fallback if using GPT-4o
    GOOGLE_AI_API_KEY: str = ""              # Gemini
    DEEPL_API_KEY: str = ""
    REPLICATE_API_TOKEN: str = ""            # for Whisper inference

    # ── Meeting Bot ───────────────────────────────────────────────────────────
    BOT_PROVIDER: str = "mock"               # mock | recall | custom
    RECALL_AI_API_KEY: str = ""
    RECALL_AI_REGION: str = "us-east-1"    # recall.ai region (us-east-1, us-west-2, eu-central-1, etc.)
    RECALL_AI_WEBHOOK_URL: str = ""          # your public URL for audio chunks

    # ── Storage ───────────────────────────────────────────────────────────────
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "ai-meeting-assistant"
    R2_PUBLIC_URL: str = ""

    # ── Email ─────────────────────────────────────────────────────────────────
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "noreply@yourdomain.com"
    EMAIL_FROM_NAME: str = "AI Meeting Assistant"

    # ── Calendar ──────────────────────────────────────────────────────────────
    GOOGLE_CALENDAR_SCOPES: List[str] = [
        "openid", "email", "profile",
        "https://www.googleapis.com/auth/calendar.events",
    ]
    MICROSOFT_GRAPH_SCOPES: List[str] = [
        "openid", "email", "profile", "offline_access",
        "Calendars.ReadWrite",
    ]
    SENDGRID_API_KEY: str | None = None
    
    # ── Encryption ────────────────────────────────────────────────────────────
    ENCRYPTION_KEY: str = ""                 # Fernet key for encrypting OAuth tokens at rest

    class Config:
        env_file = ".env"
        case_sensitive = True
    
    
    # Test configuration override
    if __name__ == "__main__":
        from app.core.test_config import TestSettings
        settings = TestSettings()
settings = Settings()
