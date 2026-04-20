"""Runtime configuration. Loaded from env via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Two levels up: afters-orchestrator/afters/config.py -> Afters/.env
_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ROOT_ENV),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    anthropic_api_key: str = ""
    openai_api_key: str = ""

    mongodb_uri: str = "mongodb://localhost:27017/afters"
    mongo_db_name_override: str = ""
    redis_url: str = "redis://localhost:6379"

    mock_llm: bool = False
    timeout_seconds_override: int = 60

    messaging_base_url: str = "http://localhost:3001"
    orchestrator_base_url: str = "http://localhost:8000"

    # Feature flags for demo.
    auto_drive_scenarios: bool = True

    @property
    def mongo_db_name(self) -> str:
        # explicit override takes priority (needed for Railway-style URIs without a db path)
        if self.mongo_db_name_override:
            return self.mongo_db_name_override
        # pull last path segment from the URI
        candidate = self.mongodb_uri.rstrip("/").rsplit("/", 1)[-1] or "afters"
        # safety: if the candidate contains invalid mongo db name characters,
        # fall back to the default
        if any(c in candidate for c in ".$/\\ \""):
            return "afters"
        return candidate


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
