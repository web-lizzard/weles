from typing import Protocol

from pydantic import BaseModel

from domain.distill.card import Card
from domain.distill.note import Note
from domain.distill.value_objects import CardId, NoteId
from domain.shared.instruction.model import Instruction


class NoteRepository(Protocol):
    async def save(self, note: Note) -> None: ...

    async def get(self, note_id: NoteId) -> Note | None: ...

    async def list_all(self) -> list[Note]: ...


class CardRepository(Protocol):
    async def save(self, card: Card) -> None: ...

    async def get(self, card_id: CardId) -> Card | None: ...

    async def list_by_note(self, note_id: NoteId) -> list[Card]: ...


class StructuredTaskPort(Protocol):
    """One model call that answers with one typed result — the port every
    phase of a card-generation run is dispatched through.

    The whole of what the model is asked travels in the arguments: the
    instruction is what to do, and `output` is the shape to answer in, both
    declared by the phase. The port knows no phase and no flow, so an adapter
    has nothing to dispatch on — a new phase is a new declaration in the
    domain, never a new adapter branch.

    Nothing else crosses: no phase name, no run id. An adapter names its trace
    span from `output`, and the calls of one run are grouped by a parent span
    the worker handler opens around the command — so tracing needs no argument
    that the domain would have to supply and nothing would read.

    A result that does not validate against `output` is the adapter's to retry
    or raise; the port never returns a partial or unvalidated result.

    Held by the application command, never by the machine — the same placement
    as `CaptureAgentPort` (`domain/capture/ports.py`).
    """

    async def complete[OutputT: BaseModel](
        self,
        instruction: Instruction,
        output: type[OutputT],
    ) -> OutputT: ...
