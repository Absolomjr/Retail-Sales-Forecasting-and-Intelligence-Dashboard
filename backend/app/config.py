"""Runtime configuration.

Everything is overridable by environment variable, so the same image runs
locally against parquet files and in Docker against Postgres.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_artifacts() -> Path:
    """`<repo>/artifacts`, resolved relative to this file."""
    return (Path(__file__).resolve().parents[2] / "artifacts")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RSF_", env_file=".env", extra="ignore")

    artifacts_dir: Path = _default_artifacts()

    #: Optional SQLAlchemy URL. When set, the analytics tables are read from the
    #: database instead of the parquet files. The parquet files remain the source
    #: of truth and the seeding script loads them in.
    database_url: str | None = None

    #: Browser origins allowed to call the API.
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:4173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    #: Longest horizon the model is allowed to be asked for. The model is a
    #: *direct* 28-day forecaster; beyond that its features are undefined.
    max_horizon: int = 28

    api_title: str = "Retail Sales Forecasting API"
    api_version: str = "1.0.0"


settings = Settings()
