"""Backward-compatible entrypoint when invoking `pytest tests/bdd`."""

from features.test_bdd import *  # noqa: F403
