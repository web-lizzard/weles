from adapters.auth.model import AttemptAction, AttemptLimits, AttemptSource


class InMemoryAttemptLedger:
    """`AttemptLedger` for acceptance and unit tests."""

    def __init__(self, limits: AttemptLimits) -> None:
        self._limits: AttemptLimits = limits

    async def ensure_allowed(
        self, action: AttemptAction, source: AttemptSource
    ) -> None:
        del action, source
        raise NotImplementedError

    async def record(self, action: AttemptAction, source: AttemptSource) -> None:
        del action, source
        raise NotImplementedError

    async def clear(self, action: AttemptAction, source: AttemptSource) -> None:
        del action, source
        raise NotImplementedError
