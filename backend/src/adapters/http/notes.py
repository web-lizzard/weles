from typing import Annotated

from fastapi import APIRouter, Depends

from adapters.compose import get_list_notes_query
from application.distill.queries.list_notes import (
    ListNotesQueryPort,
    NoteListItemDTO,
)

router = APIRouter()


@router.get("/notes")
async def list_notes(
    query: Annotated[  # pyright: ignore[reportUnusedParameter]
        ListNotesQueryPort, Depends(get_list_notes_query)
    ],
) -> list[NoteListItemDTO]:
    raise NotImplementedError
