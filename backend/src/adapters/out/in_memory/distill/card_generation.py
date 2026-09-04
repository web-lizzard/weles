from application.distill.value_objects import CardProposal
from domain.distill.value_objects import NoteContent


class DeterministicCardGenerationAdapter:
    async def generate(self, _content: NoteContent) -> list[CardProposal]: ...
