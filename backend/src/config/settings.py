from enum import StrEnum
from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    LOCAL = "local"
    STAGING = "staging"
    PROD = "prod"


class Settings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    database_url: str
    notion_api_token: str | None = None
    vocabulary_match_threshold: float = 0.85
    environment_name: Environment = Environment.LOCAL
    outbox_poll_interval_seconds: float = 1.0
    outbox_batch_size: int = 10
    outbox_max_attempts: int = 3
    outbox_worker_id: str = "note-save-worker"
