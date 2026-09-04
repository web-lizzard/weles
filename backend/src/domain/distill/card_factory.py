from domain.distill.card import Card
from domain.distill.value_objects import (
    Anchor,
    AnchorResolution,
    CardLengthPolicy,
    CardSide,
    NoteId,
)


class CardFactory:
    def __init__(self, length_policy: CardLengthPolicy) -> None:
        self._length_policy: CardLengthPolicy = length_policy

    def mint(
        self,
        _note_id: NoteId,
        _front: CardSide,
        _back: CardSide,
        _anchor: Anchor,
        _resolution: AnchorResolution,
    ) -> Card: ...
