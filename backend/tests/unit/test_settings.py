import pytest
from pydantic import ValidationError

from config.settings import Settings

_DATABASE_URL = "postgresql+asyncpg://weles:weles@postgres:5432/weles"


def test_settings_raises_when_database_url_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
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
