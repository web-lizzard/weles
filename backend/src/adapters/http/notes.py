from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from adapters.auth.router import require_sign_in
from adapters.compose import (
    get_list_cards_for_note_query,
    get_list_notes_query,
    get_note_query,
)
from application.distill.queries.get_note import GetNoteQueryPort, NoteDetailDTO
from application.distill.queries.list_cards_for_note import (
    CardListItemDTO,
    ListCardsForNoteQueryPort,
)
from application.distill.queries.list_notes import (
    ListNotesQueryPort,
    NoteListItemDTO,
)
from domain.distill.value_objects import NoteId
from domain.shared.identity.model import UserId

router = APIRouter()


@router.get("/notes")
async def list_notes(
    user_id: Annotated[UserId, Depends(require_sign_in)],
    query: Annotated[ListNotesQueryPort, Depends(get_list_notes_query)],
) -> list[NoteListItemDTO]:
    return await query.list_notes(user_id)


@router.get("/notes/{note_id}")
async def get_note(
    note_id: UUID,
    user_id: Annotated[UserId, Depends(require_sign_in)],
    query: Annotated[GetNoteQueryPort, Depends(get_note_query)],
) -> NoteDetailDTO:
    return await query.get_note(user_id, NoteId(value=note_id))


@router.get("/notes/{note_id}/cards")
async def list_cards_for_note(
    note_id: UUID,
    user_id: Annotated[UserId, Depends(require_sign_in)],
    query: Annotated[ListCardsForNoteQueryPort, Depends(get_list_cards_for_note_query)],
) -> list[CardListItemDTO]:
    return await query.list_cards_for_note(user_id, NoteId(value=note_id))
