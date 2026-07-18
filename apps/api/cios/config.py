"""Application configuration — all settings from environment variables."""
from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Application
    app_env: Literal["development", "staging", "production"] = "development"
    app_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"
    debug: bool = False

    # Database
    database_url: str = Field(..., description="Async PostgreSQL URL")
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl: int = 3600

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None

    # Anthropic
    anthropic_api_key: str = Field(..., description="Anthropic API key")
    anthropic_model_ceo: str = "claude-opus-4-8"
    anthropic_model_director: str = "claude-sonnet-4-6"
    anthropic_model_analyst: str = "claude-haiku-4-5-20251001"

    # Auth
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    jwt_secret: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60
    jwt_refresh_expiry_days: int = 30

    # Storage
    s3_endpoint: str = "https://s3.amazonaws.com"
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_bucket_documents: str = "cios-documents"
    s3_bucket_exports: str = "cios-exports"
    s3_region: str = "us-east-1"

    # Embeddings
    voyage_api_key: str = ""
    embedding_model: str = "voyage-3"

    # External APIs
    sam_gov_api_key: str = ""
    usaspending_api_key: str = ""

    # Encryption
    encryption_key: str = Field(..., min_length=64, description="32-byte hex key")
    tenant_key_derivation_salt: str = ""

    # Observability
    otel_exporter_otlp_endpoint: str = "http://localhost:4318"
    sentry_dsn: str = ""
    log_level: str = "INFO"

    # Billing
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_starter: str = ""
    stripe_price_professional: str = ""
    stripe_price_enterprise: str = ""

    # Email
    sendgrid_api_key: str = ""
    from_email: str = "noreply@cios.ai"

    # Feature flags
    feature_award_simulator: bool = True
    feature_competitive_intel: bool = True
    feature_teaming_ai: bool = True

    @field_validator("database_url", mode="before")
    @classmethod
    def validate_db_url(cls, v: str) -> str:
        if not v.startswith("postgresql"):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def cors_origins(self) -> list[str]:
        if self.is_production:
            return [self.app_url]
        return ["http://localhost:3000", "http://localhost:3001", self.app_url]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
