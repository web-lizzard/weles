import asyncio
import math
from datetime import UTC, datetime, timedelta

from adapters.auth.exceptions import TooManyAttemptsError
from adapters.auth.model import AttemptAction, AttemptLimits, AttemptSource


class InMemoryAttemptLedger:
    """`AttemptLedger` for acceptance and unit tests."""

    def __init__(self, limits: AttemptLimits) -> None:
        self._limits: AttemptLimits = limits
        self._lock: asyncio.Lock = asyncio.Lock()
        self._attempts: dict[tuple[AttemptAction, str], list[datetime]] = {}

    async def ensure_allowed(
        self, action: AttemptAction, source: AttemptSource
    ) -> None:
        limit = self._limits.for_action(action)
        async with self._lock:
            timestamps = self._pruned(action, source, limit.window)
            if len(timestamps) < limit.max_attempts:
                return
            oldest = timestamps[0]
            remaining = (oldest + limit.window) - datetime.now(UTC)
            retry_after_seconds = max(1, math.ceil(remaining.total_seconds()))
            raise TooManyAttemptsError(retry_after_seconds=retry_after_seconds)

    async def record(self, action: AttemptAction, source: AttemptSource) -> None:
        limit = self._limits.for_action(action)
        async with self._lock:
            timestamps = self._pruned(action, source, limit.window)
            timestamps.append(datetime.now(UTC))
            self._attempts[(action, source.value)] = timestamps

    async def clear(self, action: AttemptAction, source: AttemptSource) -> None:
        async with self._lock:
            _ = self._attempts.pop((action, source.value), None)

    def _pruned(
        self, action: AttemptAction, source: AttemptSource, window: timedelta
    ) -> list[datetime]:
        cutoff = datetime.now(UTC) - window
        key = (action, source.value)
        timestamps = [t for t in self._attempts.get(key, []) if t >= cutoff]
        self._attempts[key] = timestamps
        return timestamps
