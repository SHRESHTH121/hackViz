"""Runtime configuration, read from environment variables / backend/.env."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent
load_dotenv(BACKEND_DIR / ".env")


class ConfigError(RuntimeError):
    pass


def _bool(v: str | None, default: bool) -> bool:
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    database_url: str
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_timeout: float = 240.0
    batch_size: int = 5
    idle_seconds: int = 90
    retry_seconds: int = 60
    max_recent_events: int = 35
    auto_analysis: bool = True
    org_utc_offset_minutes: int = 330
    cors_origins: list[str] = field(default_factory=list)
    data_dir: Path = PROJECT_DIR / "data" / "generated"

    @property
    def org_tz(self) -> timezone:
        return timezone(timedelta(minutes=self.org_utc_offset_minutes))


def load_settings() -> Settings:
    db = os.getenv("DATABASE_URL", "").strip()
    if not db:
        raise ConfigError("DATABASE_URL is not set. Copy backend/.env.example to backend/.env and configure PostgreSQL.")
    if not db.startswith("postgresql"):
        # PostgreSQL is mandatory - refuse anything else instead of silently falling back.
        raise ConfigError(f"DATABASE_URL must be a PostgreSQL URL (postgresql+psycopg://...), got '{db.split(':')[0]}'.")
    if db.startswith("postgresql://"):
        db = "postgresql+psycopg://" + db[len("postgresql://"):]

    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
    host = urlparse(ollama_url).hostname or ""
    if host not in ("localhost", "127.0.0.1", "::1"):
        raise ConfigError("OLLAMA_URL must point to a local Ollama instance (localhost / 127.0.0.1).")

    return Settings(
        database_url=db,
        ollama_url=ollama_url,
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
        ollama_timeout=float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "240")),
        batch_size=max(1, int(os.getenv("ANALYSIS_BATCH_SIZE", "5"))),
        idle_seconds=max(10, int(os.getenv("ANALYSIS_IDLE_SECONDS", "90"))),
        retry_seconds=max(5, int(os.getenv("ANALYSIS_RETRY_SECONDS", "60"))),
        max_recent_events=min(60, max(5, int(os.getenv("ANALYSIS_MAX_RECENT_EVENTS", "35")))),
        auto_analysis=_bool(os.getenv("ANALYSIS_AUTO_ENABLED"), True),
        org_utc_offset_minutes=int(os.getenv("ORG_UTC_OFFSET_MINUTES", "330")),
        cors_origins=[o.strip() for o in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()],
    )


settings = load_settings()
