"""Repository-wide pytest hooks."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

# Keep the suite offline: production defaults to OpenRouter + tracing on.
# Applied at module level, before pytest_plugins below imports
# integration.support.postgres, which in turn imports adapters.compose and
# triggers its import-time Settings() — pytest_configure runs too late for that.
_ = os.environ.setdefault("EMBEDDING_PROVIDER", "deterministic")
_ = os.environ.setdefault("CAPTURE_AGENT_PROVIDER", "deterministic")
_ = os.environ.setdefault("DISTILL_TASK_PROVIDER", "deterministic")
_ = os.environ.setdefault("TRACING_ENABLED", "false")
_ = os.environ.setdefault("AUTH_SIGNING_SECRET", "test-only-auth-signing-secret-32b")
_ = os.environ.setdefault("OPENROUTER_API_KEY", "test-only-openrouter-api-key")

_test_database_url = os.environ.get("TEST_DATABASE_URL")
_ = os.environ.setdefault(
    "DATABASE_URL",
    make_url(_test_database_url)
    .set(database="postgres")
    .render_as_string(hide_password=False)
    if _test_database_url
    else "postgresql+asyncpg://placeholder:placeholder@127.0.0.1:1/placeholder",
)

pytest_plugins = ["integration.support.postgres"]

_TESTS_ROOT = Path(__file__).resolve().parent
_FEATURES_LOADER = _TESTS_ROOT / "features" / "test_bdd.py"
_BDD_SHIM = _TESTS_ROOT / "bdd" / "test_features.py"


def pytest_ignore_collect(collection_path: Path, config: pytest.Config) -> bool:
    """Avoid collecting acceptance scenarios twice when both loaders are visible."""
    if not _FEATURES_LOADER.is_file():
        return False
    path = Path(str(collection_path)).resolve()
    if path != _BDD_SHIM.resolve():
        return False
    args = list(config.args)
    if not args:
        return True
    for arg in args:
        normalized = Path(arg)
        parts = normalized.parts
        if "features" in parts:
            return True
        if normalized.name == "test_bdd.py":
            return True
        if normalized in (Path("tests"), Path("tests/")):
            return True
    return False
