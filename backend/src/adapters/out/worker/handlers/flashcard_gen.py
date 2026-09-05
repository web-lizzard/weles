from application.distill.commands.generate_cards import GenerateCardsCommand
from domain.distill.outbox import NOTE_SAVED
from domain.shared.outbox.model import EnvelopeType, OutboxEnvelope


class FlashcardGenHandler:
    envelope_type: EnvelopeType = NOTE_SAVED

    def __init__(self, command: GenerateCardsCommand) -> None:
        self._command: GenerateCardsCommand = command

    async def handle(self, _envelope: OutboxEnvelope) -> None: ...
