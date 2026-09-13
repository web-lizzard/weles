import json
from enum import StrEnum
from typing import ClassVar, cast

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    LOCAL = "local"
    STAGING = "staging"
    PROD = "prod"


class EmbeddingProvider(StrEnum):
    DETERMINISTIC = "deterministic"
    OPENROUTER = "openrouter"


class CaptureAgentProvider(StrEnum):
    DETERMINISTIC = "deterministic"
    PYDANTIC_AI = "pydantic_ai"


class DistillTaskProvider(StrEnum):
    DETERMINISTIC = "deterministic"
    PYDANTIC_AI = "pydantic_ai"


_DEFAULT_DISTILL_REGENERATION_TIERS: list[tuple[int | None, float]] = [
    (1500, 0.5),
    (6000, 0.6),
    (None, 0.7),
]


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
    capture_agent_provider: CaptureAgentProvider = CaptureAgentProvider.PYDANTIC_AI
    openrouter_api_key: str | None = None
    embedding_model: str = "openai/text-embedding-3-small"
    embedding_dimensions: int | None = None
    capture_model: str = "openai/gpt-4o-mini"
    distill_task_provider: DistillTaskProvider = DistillTaskProvider.PYDANTIC_AI
    distill_model: str = "openai/gpt-4o-mini"
    distill_regeneration_tiers: list[tuple[int | None, float]] = (
        _DEFAULT_DISTILL_REGENERATION_TIERS
    )
    tracing_enabled: bool = True
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_otlp_endpoint: str = "https://cloud.langfuse.com/api/public/otel/v1/traces"

    @field_validator("distill_regeneration_tiers", mode="before")
    @classmethod
    def _parse_distill_regeneration_tiers(cls, value: object) -> object:
        if isinstance(value, str):
            parsed = cast(
                list[list[int | None | float]],
                json.loads(value),
            )
            return [(row[0], row[1]) for row in parsed]
        return value
