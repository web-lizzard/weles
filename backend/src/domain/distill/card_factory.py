from datetime import UTC, datetime
from uuid import uuid4

from domain.distill.card import Card
from domain.distill.value_objects import (
    Anchor,
    AnchorResolution,
    CardId,
    CardLengthPolicy,
    CardSide,
    Discard,
    DiscardReason,
    NoteId,
)
from domain.shared.identity.model import UserId


class CardFactory:
    def __init__(self, length_policy: CardLengthPolicy) -> None:
        self._length_policy: CardLengthPolicy = length_policy

    def mint(
        self,
        owner_id: UserId,
        note_id: NoteId,
        front: CardSide,
        back: CardSide,
        anchor: Anchor,
        resolution: AnchorResolution,
    ) -> Card:
        card = Card(
            id=CardId(value=uuid4()),
            owner_id=owner_id,
            note_id=note_id,
            front=front,
            back=back,
            anchor=anchor,
            discard=None,
            created_at=datetime.now(UTC),
        )
        card.discard = self._verdict(front, back, resolution)
        return card

    def _verdict(
        self,
        front: CardSide,
        back: CardSide,
        resolution: AnchorResolution,
    ) -> Discard | None:
        if resolution is AnchorResolution.UNRESOLVED:
            return Discard(
                reason=DiscardReason.UNGROUNDED,
                detail=None,
                discarded_at=datetime.now(UTC),
            )
        breach = self._length_policy.breach(front, back)
        if breach is not None:
            return Discard(
                reason=DiscardReason.OVERSIZED,
                detail=breach,
                discarded_at=datetime.now(UTC),
            )
        return None
