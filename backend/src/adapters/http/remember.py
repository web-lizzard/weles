# pyright: reportUnusedParameter=false
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from adapters.compose import (
    get_current_card_query,
    get_grade_card_command,
    get_open_sitting_command,
    get_reveal_back_query,
)
from application.remember.commands.grade_card import GradeCardCommand
from application.remember.commands.open_sitting import OpenSittingCommand
from application.remember.dto import (
    GradeAppliedDTO,
    GradeRequestDTO,
    NothingDueDTO,
    PresentedCardDTO,
    RevealedCardDTO,
    SittingOpenedDTO,
)
from application.remember.queries.current_card import CurrentCardQuery
from application.remember.queries.reveal_back import RevealBackQuery

router = APIRouter()


@router.post("/review-sittings")
async def open_sitting(
    command: Annotated[OpenSittingCommand, Depends(get_open_sitting_command)],
) -> SittingOpenedDTO | NothingDueDTO: ...


@router.get("/review-sittings/{sitting_id}/current-card")
async def current_card(
    sitting_id: UUID,
    query: Annotated[CurrentCardQuery, Depends(get_current_card_query)],
) -> PresentedCardDTO: ...


@router.get("/review-sittings/{sitting_id}/cards/{card_id}/back")
async def reveal_back(
    sitting_id: UUID,
    card_id: UUID,
    query: Annotated[RevealBackQuery, Depends(get_reveal_back_query)],
) -> RevealedCardDTO: ...


@router.post("/review-sittings/{sitting_id}/cards/{card_id}/grade")
async def grade_card(
    sitting_id: UUID,
    card_id: UUID,
    body: GradeRequestDTO,
    command: Annotated[GradeCardCommand, Depends(get_grade_card_command)],
) -> GradeAppliedDTO: ...
