# pyright: reportUnusedParameter=false
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from adapters.compose import (
    get_current_card_query,
    get_due_count_query,
    get_grade_card_command,
    get_open_sitting_command,
    get_reveal_back_query,
)
from application.remember.commands.grade_card import GradeCardCommand
from application.remember.commands.open_sitting import OpenSittingCommand
from application.remember.dto import (
    DueCountDTO,
    GradeAppliedDTO,
    GradeRequestDTO,
    NothingDueDTO,
    PresentedCardDTO,
    RevealedCardDTO,
    SittingOpenedDTO,
    SittingResumedDTO,
)
from application.remember.queries.current_card import CurrentCardQuery
from application.remember.queries.due_count import DueCountQuery
from application.remember.queries.reveal_back import RevealBackQuery
from domain.remember.value_objects import CardId, SittingId

router = APIRouter()


@router.get("/due-cards/count")
async def due_cards_count(
    query: Annotated[DueCountQuery, Depends(get_due_count_query)],
) -> DueCountDTO:
    return await query.handle()


@router.post("/review-sittings")
async def open_sitting(
    command: Annotated[OpenSittingCommand, Depends(get_open_sitting_command)],
) -> SittingOpenedDTO | SittingResumedDTO | NothingDueDTO:
    return await command.handle()


@router.get("/review-sittings/{sitting_id}/current-card")
async def current_card(
    sitting_id: UUID,
    query: Annotated[CurrentCardQuery, Depends(get_current_card_query)],
) -> PresentedCardDTO:
    return await query.handle(SittingId(value=sitting_id))


@router.get("/review-sittings/{sitting_id}/cards/{card_id}/back")
async def reveal_back(
    sitting_id: UUID,
    card_id: UUID,
    query: Annotated[RevealBackQuery, Depends(get_reveal_back_query)],
) -> RevealedCardDTO:
    return await query.handle(SittingId(value=sitting_id), CardId(value=card_id))


@router.post("/review-sittings/{sitting_id}/cards/{card_id}/grade")
async def grade_card(
    sitting_id: UUID,
    card_id: UUID,
    body: GradeRequestDTO,
    command: Annotated[GradeCardCommand, Depends(get_grade_card_command)],
) -> GradeAppliedDTO:
    return await command.handle(
        SittingId(value=sitting_id), CardId(value=card_id), body.grade
    )
