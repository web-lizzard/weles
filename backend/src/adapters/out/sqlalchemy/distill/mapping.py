from adapters.out.sqlalchemy.distill.models import (
    DistillCardRow,
    DistillNoteRow,
    DistillNoteTagRow,
)
from domain.distill.card import Card
from domain.distill.note import Note
from domain.distill.value_objects import Discard, TagSnapshot, TopicSnapshot


def note_to_row(note: Note) -> DistillNoteRow:
    return DistillNoteRow(
        id=note.id,
        session_id=note.session_id,
        topic_id=note.topic.id,
        topic_label=note.topic.label,
        content=note.content,
        distillation_status=note.distillation_status,
        approved_at=note.approved_at,
        created_at=note.created_at,
        updated_at=note.updated_at,
        tags=[
            DistillNoteTagRow(
                note_id=note.id,
                position=position,
                tag_id=tag.id,
                label=tag.label,
            )
            for position, tag in enumerate(note.tags)
        ],
    )


def note_to_domain(row: DistillNoteRow) -> Note:
    return Note(
        id=row.id,
        session_id=row.session_id,
        topic=TopicSnapshot(id=row.topic_id, label=row.topic_label),
        content=row.content,
        tags=[TagSnapshot(id=tag.tag_id, label=tag.label) for tag in row.tags],
        distillation_status=row.distillation_status,
        approved_at=row.approved_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _discard_from_row(row: DistillCardRow) -> Discard | None:
    if row.discard_reason is None:
        return None
    return Discard(
        reason=row.discard_reason,
        detail=row.discard_detail,
        discarded_at=row.discarded_at,  # pyright: ignore[reportArgumentType]
    )


def card_to_row(card: Card) -> DistillCardRow:
    discard = card.discard
    return DistillCardRow(
        id=card.id,
        note_id=card.note_id,
        front=card.front,
        back=card.back,
        anchor_quote=card.anchor,
        discard_reason=discard.reason if discard is not None else None,
        discard_detail=discard.detail if discard is not None else None,
        discarded_at=discard.discarded_at if discard is not None else None,
        created_at=card.created_at,
    )


def card_to_domain(row: DistillCardRow) -> Card:
    return Card(
        id=row.id,
        note_id=row.note_id,
        front=row.front,
        back=row.back,
        anchor=row.anchor_quote,
        discard=_discard_from_row(row),
        created_at=row.created_at,
    )
