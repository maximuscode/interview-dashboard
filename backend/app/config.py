from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Runtime configuration, overridable via APP_-prefixed environment variables."""

    model_config = SettingsConfigDict(env_prefix="APP_")

    # Swap this for a postgresql+psycopg:// URL to run against a real Postgres.
    database_url: str = f"sqlite:///{BASE_DIR / 'interviews.db'}"

    # Fixed so the generated dataset and its AI scores are identical on every run.
    seed: int = 20260101

    interview_count: int = 60

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


settings = Settings()
