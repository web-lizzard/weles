import asyncio
import logging
from collections.abc import Sequence

from application.shared.outbox.ports import OutboxHandler
from domain.shared.outbox.model import EnvelopeStatus, OutboxEnvelope
from domain.shared.outbox.ports import OutboxClaimer

logger = logging.getLogger(__name__)


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
        acked = 0
        for handler in self._handlers:
            envelopes = await self._claimer.claim(
                handler.envelope_type, self._batch_size, self._worker_id
            )
            for envelope in envelopes:
                logger.info(
                    "outbox worker %s claimed envelope %s type=%s",
                    self._worker_id,
                    envelope.id,
                    handler.envelope_type,
                )
            results = await asyncio.gather(
                *(self._process(handler, envelope) for envelope in envelopes)
            )
            acked += sum(results)
        return acked

    async def run_forever(self, interval_seconds: float) -> None:
        while True:
            try:
                _ = await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "outbox worker %s failed during run_once", self._worker_id
                )
            await asyncio.sleep(interval_seconds)

    async def _process(self, handler: OutboxHandler, envelope: OutboxEnvelope) -> bool:
        try:
            await handler.handle(envelope)
        except Exception:
            envelope.fail(self._max_attempts)
            await self._claimer.fail(envelope)
            if envelope.status == EnvelopeStatus.FAILED:
                logger.error(
                    "outbox envelope %s dead-lettered after %d attempts",
                    envelope.id,
                    envelope.attempts,
                )
            else:
                logger.warning(
                    "outbox envelope %s handling failed on attempt %d",
                    envelope.id,
                    envelope.attempts,
                )
            return False
        envelope.consume()
        await self._claimer.ack(envelope)
        logger.info("outbox envelope %s acked", envelope.id)
        return True
