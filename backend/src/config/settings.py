from enum import StrEnum
from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    LOCAL = "local"
    STAGING = "staging"
    PROD = "prod"


class EmbeddingProvider(StrEnum):
    DETERMINISTIC = "deterministic"
    OPENROUTER = "openrouter"


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
    card_front_max: int = 200
    card_back_max: int = 600
    sitting_max_showings: int = 2
    sitting_resume_horizon_hours: float = 24.0
    embedding_provider: EmbeddingProvider = EmbeddingProvider.OPENROUTER
    openrouter_api_key: str | None = None
    embedding_model: str = "openai/text-embedding-3-small"
    embedding_dimensions: int | None = None
    tracing_enabled: bool = True
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_otlp_endpoint: str = "https://cloud.langfuse.com/api/public/otel/v1/traces"
