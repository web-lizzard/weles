"""Repository-wide pytest hooks."""

from __future__ import annotations

from pathlib import Path

import pytest

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
