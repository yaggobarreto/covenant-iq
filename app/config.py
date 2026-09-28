"""Application settings, read from environment variables (see .env.example)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Defaults to a local SQLite file so the app and test suite run with zero
    # external setup. Point DATABASE_URL at Postgres for production use.
    database_url: str = "sqlite:///./covenant_iq.db"

    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    openai_api_key: str | None = None

    # A covenant is "compliant" above this headroom, "early warning" between
    # this and zero, and "breach" once actual headroom drops below zero.
    early_warning_headroom_pct: float = 10.0

    # How many trailing snapshots the trend detector looks at.
    trend_window: int = 3


settings = Settings()
