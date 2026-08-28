import pytest
from pydantic import ValidationError

from config.settings import Settings


def test_settings_raises_when_database_url_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings()


def test_settings_loads_database_url_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = "postgresql+asyncpg://weles:weles@postgres:5432/weles"
    monkeypatch.setenv("DATABASE_URL", database_url)
    settings = Settings()
    assert settings.database_url == database_url
