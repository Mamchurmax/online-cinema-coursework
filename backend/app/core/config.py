"""Application configuration.

Pattern: Singleton (GoF).
`Settings` holds the whole application configuration. Exactly one instance
exists per process: it is created lazily by `Settings.instance()` and reused
by every layer (API, services, repositories). FastAPI code receives it through
the `get_settings` dependency, so tests can override it.
"""

from pathlib import Path
from typing import ClassVar, Self

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Singleton: the single source of application configuration."""

    model_config = SettingsConfigDict(
        # The backend may be started from `backend/` or from the repo root.
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Online Cinema API"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+psycopg://cinema:cinema@localhost:5432/cinema"
    cors_origins: list[str] = ["http://localhost:5173"]

    # Must be overridden in .env for any shared deployment.
    jwt_secret_key: str = "dev-only-secret-change-me-in-env-0123456789"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    tmdb_api_token: str = ""

    # Videos: MEDIA_ROOT/source holds originals, MEDIA_ROOT/hls the streams.
    # The default fits a local run from `backend/`; Docker sets MEDIA_ROOT=/media.
    media_root: Path = Path("../media")
    media_url: str = "/media/hls"

    @property
    def hls_root(self) -> Path:
        return self.media_root / "hls"

    _instance: ClassVar[Self | None] = None

    @classmethod
    def instance(cls) -> Self:
        """Return the only `Settings` instance, creating it on first access."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


def get_settings() -> Settings:
    """FastAPI dependency that provides the `Settings` singleton."""
    return Settings.instance()
