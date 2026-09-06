from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from adapters.compose import get_list_notes_query, get_note_query
from application.distill.queries.get_note import GetNoteQueryPort, NoteDetailDTO
from application.distill.queries.list_notes import (
    ListNotesQueryPort,
    NoteListItemDTO,
)

router = APIRouter()


@router.get("/notes")
async def list_notes(
    query: Annotated[ListNotesQueryPort, Depends(get_list_notes_query)],
) -> list[NoteListItemDTO]:
    return await query.list_notes()


@router.get("/notes/{note_id}")
async def get_note(
    note_id: UUID,
    query: Annotated[GetNoteQueryPort, Depends(get_note_query)],
) -> NoteDetailDTO:
    raise NotImplementedError(note_id, query)
