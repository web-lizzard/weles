from adapters.auth.model import AttemptAction, AttemptLimits, AttemptSource


class InMemoryAttemptLedger:
    """`AttemptLedger` for acceptance and unit tests."""

    def __init__(self, limits: AttemptLimits) -> None:
        self._limits: AttemptLimits = limits

    async def ensure_allowed(
        self, _action: AttemptAction, _source: AttemptSource
    ) -> None:
        raise NotImplementedError

    async def record(self, _action: AttemptAction, _source: AttemptSource) -> None:
        raise NotImplementedError

    async def clear(self, _action: AttemptAction, _source: AttemptSource) -> None:
        raise NotImplementedError
