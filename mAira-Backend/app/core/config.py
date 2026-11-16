"""Application Configuration using Pydantic Settings with Zero Insecure Fallbacks."""

import os
from functools import lru_cache
from typing import List, Optional
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.security.secrets import get_secret


class Settings(BaseSettings):
    """Central typed settings for MAIRA Phase 1 backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Environment
    ENVIRONMENT: str = "development"
    APP_NAME: str = "MAira"
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # PostgreSQL Database
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 5432
    DB_NAME: str = "mira_db"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = Field(default_factory=lambda: get_secret("DB_PASSWORD", default="", required=False))
    DB_SCHEMA: str = "sch_con"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_PRE_PING: bool = True

    # Test Database Isolation
    TEST_DB_NAME: str = "mira_test_db"
    TEST_DATABASE_URL: Optional[str] = None

    @property
    def database_url_async(self) -> str:
        """Construct asyncpg connection URL."""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def database_url_sync(self) -> str:
        """Construct psycopg2 connection URL."""
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # JWT Authentication & Session Management
    JWT_SECRET_KEY: str = Field(default_factory=lambda: get_secret("JWT_SECRET_KEY", default="", required=False))
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "maira-backend"
    JWT_AUDIENCE: str = "maira-api"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Registration & OTP
    OTP_EXPIRY_MINUTES: int = 5
    OTP_MAX_ATTEMPTS: int = 5
    REGISTRATION_TICKET_EXPIRE_MINUTES: int = 10

    # MFA Configuration
    MFA_ENABLED: bool = True  # Phase 1 two-step email MFA enabled
    MFA_EXPIRY_MINUTES: int = 5

    # Email Dispatch
    EMAIL_PROVIDER: str = "mock"  # 'mock', 'console', or 'smtp'
    EMAIL_HOST: str = "smtp.institution.edu"
    EMAIL_PORT: int = 587
    EMAIL_USE_TLS: bool = True
    EMAIL_TIMEOUT: int = 10
    EMAIL_USERNAME: str = Field(default_factory=lambda: get_secret("EMAIL_USERNAME", default="", required=False))
    EMAIL_PASSWORD: str = Field(default_factory=lambda: get_secret("EMAIL_PASSWORD", default="", required=False))
    EMAIL_FROM_ADDRESS: str = "noreply@institution.edu"
    EMAIL_FROM_NAME: str = "MAira Support"
    ALLOWED_EMAIL_DOMAINS_RAW: str = "institution.edu,gmail.com,example.com"

    @property
    def allowed_email_domains(self) -> List[str]:
        return [d.strip().lower() for d in self.ALLOWED_EMAIL_DOMAINS_RAW.split(",") if d.strip()]

    # Gen AI Microservice
    GENAI_BASE_URL: str = "http://127.0.0.1:8001"
    GENAI_SERVICE_SECRET: str = Field(default_factory=lambda: get_secret("GENAI_SERVICE_SECRET", default="", required=False))
    GENAI_CONNECT_TIMEOUT_SECONDS: float = 5.0
    GENAI_READ_TIMEOUT_SECONDS: float = 30.0
    GENAI_MAX_RETRIES: int = 2

    # CORS & Security
    CORS_ALLOW_ORIGINS_RAW: str = "http://localhost:3000,http://127.0.0.1:3000"
    CORS_ALLOW_CREDENTIALS: bool = True

    @property
    def cors_allow_origins(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ALLOW_ORIGINS_RAW.split(",") if origin.strip()]

    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LOGIN_MAX: int = 10
    RATE_LIMIT_LOGIN_WINDOW_SECONDS: int = 60
    RATE_LIMIT_OTP_MAX: int = 5
    RATE_LIMIT_OTP_WINDOW_SECONDS: int = 300
    RATE_LIMIT_CHAT_MAX: int = 30
    RATE_LIMIT_CHAT_WINDOW_SECONDS: int = 60

    @model_validator(mode="after")
    def validate_production_and_entropy(self) -> "Settings":
        is_prod = self.ENVIRONMENT.lower() == "production"

        # Validate JWT Secret Key
        if not self.JWT_SECRET_KEY:
            if is_prod:
                raise ValueError("JWT_SECRET_KEY is mandatory in production and must not be empty.")
            # In local development without .env, provide an informative error
            self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev_insecure_key_must_be_set_in_env_file_32bytes!")

        if len(self.JWT_SECRET_KEY.encode("utf-8")) < 32:
            raise ValueError("JWT_SECRET_KEY must contain at least 32 bytes (256 bits of entropy).")

        # Production-specific validations
        if is_prod:
            insecure_markers = ["dev_", "insecure", "changeme", "fallback", "example", "default"]
            if any(m in self.JWT_SECRET_KEY.lower() for m in insecure_markers):
                raise ValueError("Production JWT_SECRET_KEY must not use development fallback values.")

            if self.DEBUG:
                raise ValueError("DEBUG mode must be disabled in production.")

            if not self.MFA_ENABLED:
                raise ValueError("MFA_ENABLED is mandatory and must be True in production.")

            if not self.GENAI_SERVICE_SECRET:
                raise ValueError("GENAI_SERVICE_SECRET is mandatory in production.")
            if len(self.GENAI_SERVICE_SECRET.encode("utf-8")) < 16:
                raise ValueError("GENAI_SERVICE_SECRET must be at least 16 bytes in production.")

            if not self.DB_PASSWORD:
                raise ValueError("DB_PASSWORD is mandatory in production.")

            if self.DB_NAME == self.TEST_DB_NAME:
                raise ValueError("Production database name cannot be the test database name.")

            if self.EMAIL_PROVIDER == "mock":
                raise ValueError("EMAIL_PROVIDER cannot be 'mock' in production.")

            if self.EMAIL_PROVIDER == "smtp":
                if not self.EMAIL_HOST or not self.EMAIL_USERNAME or not self.EMAIL_PASSWORD:
                    raise ValueError("EMAIL_HOST, EMAIL_USERNAME, and EMAIL_PASSWORD are required when using SMTP in production.")

            if "*" in self.cors_allow_origins:
                raise ValueError("Wildcard '*' CORS origin is strictly forbidden in production.")

        return self


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
