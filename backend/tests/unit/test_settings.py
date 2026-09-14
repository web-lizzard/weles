from pathlib import Path

import pytest
from pydantic import ValidationError
from pydantic_settings import SettingsConfigDict

from config.settings import Settings

_DATABASE_URL = "postgresql+asyncpg://weles:weles@postgres:5432/weles"


def test_settings_raises_when_database_url_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    env_file = tmp_path / ".env"
    monkeypatch.setattr(
        Settings,
        "model_config",
        SettingsConfigDict(
            env_file=str(env_file),
            env_file_encoding="utf-8",
            extra="forbid",
        ),
    )
    with pytest.raises(ValidationError):
        _ = Settings()  # pyright: ignore[reportCallIssue]


def test_settings_loads_database_url_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", _DATABASE_URL)
    settings = Settings()  # pyright: ignore[reportCallIssue]
    assert settings.database_url == _DATABASE_URL


def test_settings_defaults_vocabulary_match_threshold_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", _DATABASE_URL)
    monkeypatch.delenv("VOCABULARY_MATCH_THRESHOLD", raising=False)
    settings = Settings()  # pyright: ignore[reportCallIssue]
    assert settings.vocabulary_match_threshold == 0.85


def test_settings_loads_vocabulary_match_threshold_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", _DATABASE_URL)
    monkeypatch.setenv("VOCABULARY_MATCH_THRESHOLD", "0.5")
    settings = Settings()  # pyright: ignore[reportCallIssue]
    assert settings.vocabulary_match_threshold == 0.5


def test_settings_defaults_distill_task_provider_to_pydantic_ai_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", _DATABASE_URL)
    monkeypatch.delenv("DISTILL_TASK_PROVIDER", raising=False)
    settings = Settings()  # pyright: ignore[reportCallIssue]
    provider = getattr(settings, "distill_task_provider", None)
    assert provider is not None
    assert str(provider) == "pydantic_ai"  # pyright: ignore[reportAny]


def test_settings_defaults_distill_model_when_unset(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DATABASE_URL", _DATABASE_URL)
    monkeypatch.delenv("DISTILL_MODEL", raising=False)
    env_file = tmp_path / ".env"
    monkeypatch.setattr(
        Settings,
        "model_config",
        SettingsConfigDict(
            env_file=str(env_file),
            env_file_encoding="utf-8",
            extra="forbid",
        ),
    )
    settings = Settings()  # pyright: ignore[reportCallIssue]
    assert settings.distill_model == "openai/gpt-5.6-luna"


def test_settings_raises_when_auth_signing_secret_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DATABASE_URL", _DATABASE_URL)
    monkeypatch.delenv("AUTH_SIGNING_SECRET", raising=False)
    env_file = tmp_path / ".env"
    monkeypatch.setattr(
        Settings,
        "model_config",
        SettingsConfigDict(
            env_file=str(env_file),
            env_file_encoding="utf-8",
            extra="forbid",
        ),
    )
    with pytest.raises(ValidationError):
        _ = Settings()  # pyright: ignore[reportCallIssue]


def test_settings_defaults_distill_regeneration_tiers_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", _DATABASE_URL)
    monkeypatch.delenv("DISTILL_REGENERATION_TIERS", raising=False)
    settings = Settings()  # pyright: ignore[reportCallIssue]
    assert getattr(settings, "distill_regeneration_tiers", None) == [
        (1500, 0.5),
        (6000, 0.6),
        (None, 0.7),
    ]


def test_settings_loads_distill_regeneration_tiers_from_json_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", _DATABASE_URL)
    monkeypatch.setenv(
        "DISTILL_REGENERATION_TIERS",
        "[[100, 0.4], [null, 0.9]]",
    )
    settings = Settings()  # pyright: ignore[reportCallIssue]
    assert getattr(settings, "distill_regeneration_tiers", None) == [
        (100, 0.4),
        (None, 0.9),
    ]
