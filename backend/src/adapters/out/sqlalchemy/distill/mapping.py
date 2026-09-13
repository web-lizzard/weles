# pyright: reportUnusedParameter=false

from adapters.out.sqlalchemy.distill.models import DistillCardRow, DistillNoteRow
from domain.distill.card import Card
from domain.distill.note import Note


def note_to_row(note: Note) -> DistillNoteRow:
    raise NotImplementedError


def note_to_domain(row: DistillNoteRow) -> Note:
    raise NotImplementedError


def card_to_row(card: Card) -> DistillCardRow:
    raise NotImplementedError


def card_to_domain(row: DistillCardRow) -> Card:
    raise NotImplementedError
