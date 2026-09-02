from collections.abc import Sequence

from application.shared.outbox.ports import OutboxHandler
from domain.shared.outbox.ports import OutboxClaimer


class OutboxWorker:
    def __init__(
        self,
        claimer: OutboxClaimer,
        handlers: Sequence[OutboxHandler],
        worker_id: str,
        batch_size: int,
        max_attempts: int,
    ) -> None:
        self._claimer: OutboxClaimer = claimer
        self._handlers: Sequence[OutboxHandler] = handlers
        self._worker_id: str = worker_id
        self._batch_size: int = batch_size
        self._max_attempts: int = max_attempts

    async def run_once(self) -> int:
        raise NotImplementedError

    async def run_forever(self, _interval_seconds: float) -> None:
        raise NotImplementedError
