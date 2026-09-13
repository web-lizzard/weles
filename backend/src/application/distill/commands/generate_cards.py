import logging
from collections.abc import Callable

from application.distill.ports import UnitOfWork
from domain.distill.card_factory import CardFactory
from domain.distill.flow import DistillMachine
from domain.distill.note_document import NoteDocument
from domain.distill.ports import StructuredTaskPort
from domain.distill.regeneration import RegenerationPolicy
from domain.distill.run import DistillRun
from domain.distill.value_objects import DistillationStatus, NoteId

logger = logging.getLogger(__name__)


class GenerateCardsCommand:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        structured_task: StructuredTaskPort,
        card_factory: CardFactory,
        regeneration_policy: RegenerationPolicy,
    ) -> None:
        self._uow_factory: Callable[[], UnitOfWork] = uow_factory
        self._structured_task: StructuredTaskPort = structured_task
        self._card_factory: CardFactory = card_factory
        self._regeneration_policy: RegenerationPolicy = regeneration_policy

    async def handle(self, note_id: NoteId) -> None:
        async with self._uow_factory() as uow:
            note = await uow.notes.get(note_id)
            if note is None:
                logger.info("note %s not found, skipping as no-op", note_id.value)
                return
            if note.distillation_status is not DistillationStatus.GENERATING:
                logger.info("note %s redelivered, skipping as no-op", note_id.value)
                return

            run = DistillRun(
                note=note,
                document=NoteDocument.of(note.content),
                policy=self._regeneration_policy,
            )
            machine = DistillMachine(run, _Deps(self._card_factory))

            try:
                while True:
                    state = machine.current_state
                    result = state.output_without_model(
                        run
                    ) or await self._structured_task.complete(
                        machine.build_instruction(), state.output
                    )
                    await machine.apply(result)
                    if not await machine.advance():
                        break
            except Exception:
                logger.exception("card generation failed for note %s", note_id.value)
                note.mark_failed()
                await uow.notes.save(note)
                await uow.commit()
                return

            if not machine.graph.is_terminal(machine.current_state_name):
                logger.error(
                    "distill run for note %s stopped outside a terminal phase: %s",
                    note_id.value,
                    machine.current_state_name,
                )
                note.mark_failed()
                await uow.notes.save(note)
                await uow.commit()
                return

            for card in run.cards():
                await uow.cards.save(card)
            note.mark_ready()
            await uow.notes.save(note)
            await uow.commit()


class _Deps:
    """The one `DistillDeps` implementation the command builds per run."""

    def __init__(self, card_factory: CardFactory) -> None:
        self._card_factory: CardFactory = card_factory

    @property
    def card_factory(self) -> CardFactory:
        return self._card_factory
