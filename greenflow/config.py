"""
GreenFlow AI – Central Configuration
=====================================
All application settings are loaded from environment variables (via .env).
Pydantic-Settings validates & types every value at startup — fail fast if anything is missing.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import AnyUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ── Project root (two levels up from this file) ──────────────────────────────
BASE_DIR = Path(__file__).resolve().parent


# ─────────────────────────────────────────────────────────────────────────────
class AppSettings(BaseSettings):
    """Core application settings."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────────
    app_name: str = Field("GreenFlow AI", description="Human-readable application name")
    app_env: str = Field("development", description="Environment: development|staging|production")
    app_debug: bool = Field(False)
    app_host: str = Field("0.0.0.0")
    app_port: int = Field(8000, ge=1, le=65535)
    secret_key: str = Field(..., description="JWT / session secret – MUST be set in .env")

    # ── OpenAI ───────────────────────────────────────────────────────────────
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_model: str = Field("gpt-4o")
    openai_embedding_model: str = Field("text-embedding-3-small")
    openai_max_tokens: int = Field(2048, ge=1)
    openai_temperature: float = Field(0.7, ge=0.0, le=2.0)

    # ── Google Gemini ───────────────────────────────────────────────────────
    google_api_key: str = Field("", description="Google Gemini API key")
    gemini_model: str = Field("gemini-2.0-flash")

    # ── HuggingFace (optional) ────────────────────────────────────────────────
    huggingface_api_key: str = Field("", description="Optional – leave blank to skip")

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = Field(
        "sqlite+aiosqlite:///./data/greenflow_dev.db",
        description="SQLAlchemy async database URL",
    )
    database_pool_size: int = Field(10, ge=1)
    database_max_overflow: int = Field(20, ge=0)

    # ── Redis ────────────────────────────────────────────────────────────────
    redis_url: str = Field("redis://localhost:6379/0")
    redis_ttl: int = Field(3600, ge=0, description="Default cache TTL in seconds")

    # ── ChromaDB ─────────────────────────────────────────────────────────────
    chroma_host: str = Field("localhost")
    chroma_port: int = Field(8001, ge=1, le=65535)
    chroma_collection: str = Field("greenflow_vectors")

    # ── Pathway ──────────────────────────────────────────────────────────────
    pathway_host: str = Field("0.0.0.0")
    pathway_port: int = Field(8080, ge=1, le=65535)
    pathway_license_key: str = Field("", description="Optional Pathway enterprise key")

    # ── Kafka / Ingestion ────────────────────────────────────────────────────
    kafka_broker: str = Field("localhost:9092")
    kafka_topic: str = Field("greenflow.events")
    kafka_group_id: str = Field("greenflow-consumer")
    data_watch_dir: str = Field("./data/watch", description="Directory Pathway polls for new files")

    @field_validator("data_watch_dir", mode="before")
    @classmethod
    def validate_data_watch_dir(cls, v: str) -> str:
        if not Path(v).is_absolute():
            abs_path = (BASE_DIR / v).resolve()
            abs_path.mkdir(parents=True, exist_ok=True)
            return str(abs_path)
        return v

    # ── Logging ──────────────────────────────────────────────────────────────
    log_level: str = Field("INFO")
    log_file: str = Field("logs/greenflow.log")
    log_rotation: str = Field("10 MB")
    log_retention: str = Field("7 days")

    # ── CORS ─────────────────────────────────────────────────────────────────
    allowed_origins: str = Field(
        "http://localhost:3000,http://localhost:5173,http://localhost:8000,http://127.0.0.1:8000",
        description="Comma-separated list of allowed CORS origins",
    )

    # ── Metrics ──────────────────────────────────────────────────────────────
    enable_metrics: bool = Field(True)
    metrics_port: int = Field(9090, ge=1, le=65535)

    # ── Computed helpers ─────────────────────────────────────────────────────
    @property
    def cors_origins(self) -> list[str]:
        """Return CORS origins as a list."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid:
            raise ValueError(f"log_level must be one of {valid}")
        return v.upper()

    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        valid = {"development", "staging", "production"}
        if v.lower() not in valid:
            raise ValueError(f"app_env must be one of {valid}")
        return v.lower()

    @field_validator("database_url", mode="before")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if v.startswith("sqlite") and "///./" in v:
            driver, rel_path = v.split("///./")
            abs_path = (BASE_DIR / rel_path).resolve()
            # Ensure the data directory exists
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            return f"{driver}///{abs_path}"
        return v

    @field_validator("log_file", mode="before")
    @classmethod
    def validate_log_file(cls, v: str) -> str:
        if not Path(v).is_absolute():
            abs_path = (BASE_DIR / v).resolve()
            # Ensure the logs directory exists
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            return str(abs_path)
        return v


# ── Singleton accessor (cached after first call) ──────────────────────────────
@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return the application settings singleton.  Import and call this everywhere."""
    return AppSettings()


# Convenience module-level alias so callers can do:  from greenflow.config import settings
settings: AppSettings = get_settings()
