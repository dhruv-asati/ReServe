"""
Application configuration.

All runtime configuration is loaded from environment variables (via a .env
file in local development). Nothing sensitive is hardcoded here — see
.env.example for the full list of variables this app expects.
"""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings, populated from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- General ---
    APP_NAME: str = "ReServe API"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = Field(default="development")  # development | staging | production
    DEBUG: bool = Field(default=True)

    # --- Database ---
    # Works with any PostgreSQL instance, including Supabase's. For Supabase,
    # copy the connection string from Project Settings -> Database and paste
    # it here (see README for exact steps). Format:
    #   postgresql+psycopg2://<user>:<password>@<host>:<port>/<database>
    DATABASE_URL: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/reserve_db"
    )

    # --- Auth ---
    JWT_SECRET: str = Field(default="CHANGE_ME_IN_PRODUCTION")
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24)  # 24 hours
    JWT_REFRESH_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24 * 7)  # 7 days

    # --- Gemini AI ---
    GEMINI_API_KEY: str = Field(default="")
    # Model used by app/services/gemini_service.py for
    # POST /api/resources/{id}/analyze. gemini-1.5-flash is fast/cheap and
    # supports response_mime_type="application/json" (structured output).
    GEMINI_MODEL: str = Field(default="gemini-1.5-flash")
    # Per-request timeout passed to the Gemini SDK. A slow/unreachable AI
    # backend should fail fast (-> 504) rather than hang the request.
    GEMINI_TIMEOUT_SECONDS: int = Field(default=20)

    # --- Supabase Storage ---
    SUPABASE_URL: str = Field(default="")
    SUPABASE_KEY: str = Field(default="")
    # Bucket that resource images are uploaded to. Must exist in the
    # Supabase project already (this app does not create buckets) and be
    # readable publicly, since uploaded resource photos need a URL anyone
    # viewing a resource listing can load.
    SUPABASE_STORAGE_BUCKET: str = Field(default="resource-images")

    # --- File uploads ---
    # Applies to both the Supabase and local-disk storage backends (see
    # app/services/storage_service.py).
    MAX_UPLOAD_FILE_SIZE_MB: int = Field(default=5)
    # Used only when Supabase isn't configured (SUPABASE_URL/SUPABASE_KEY
    # empty) — local dev falls back to writing uploads to this directory
    # and serving them back via the /static/uploads/ route mounted in
    # app/main.py.
    LOCAL_UPLOAD_DIR: str = Field(default="uploads")
    # Prefix used to build a fetchable URL for locally-stored uploads,
    # e.g. "http://localhost:8000/static/uploads/<file_id>". Irrelevant
    # once Supabase Storage is configured, since Supabase returns its own
    # absolute public URL.
    PUBLIC_BASE_URL: str = Field(default="http://localhost:8000")

    # --- CORS ---
    # Comma-separated list of allowed origins in the .env file,
    # e.g. CORS_ORIGINS=http://localhost:5173,http://localhost:3000
    CORS_ORIGINS: str = Field(default="http://localhost:5173,http://localhost:3000")

    # --- Logging ---
    LOG_LEVEL: str = Field(default="INFO")

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL must not be empty")
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse the comma-separated CORS_ORIGINS string into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.

    Using lru_cache means the .env file / environment is only read once per
    process, and the same Settings object is reused everywhere via
    dependency injection (see api routers using Depends(get_settings)).
    """
    return Settings()
