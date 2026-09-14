# pyright: reportUnusedParameter=false
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from adapters.auth.router import require_sign_in
from adapters.compose import (
    get_card_source_query,
    get_current_card_query,
    get_due_count_query,
    get_grade_card_command,
    get_open_sitting_command,
    get_reject_card_command,
    get_reveal_back_command,
)
from application.remember.commands.grade_card import GradeCardCommand
from application.remember.commands.open_sitting import OpenSittingCommand
from application.remember.commands.reject_card import RejectCardCommand
from application.remember.commands.reveal_back import RevealBackCommand
from application.remember.dto import (
    CardSourceDTO,
    DueCountDTO,
    GradeAppliedDTO,
    GradeRequestDTO,
    NothingDueDTO,
    PresentedCardDTO,
    RevealedCardDTO,
    SittingOpenedDTO,
    SittingResumedDTO,
)
from application.remember.queries.card_source import CardSourceQuery
from application.remember.queries.current_card import CurrentCardQuery
from application.remember.queries.due_count import DueCountQuery
from domain.remember.value_objects import CardId, SittingId
from domain.shared.identity.model import UserId

router = APIRouter()


@router.get("/due-cards/count")
async def due_cards_count(
    user_id: Annotated[UserId, Depends(require_sign_in)],
    query: Annotated[DueCountQuery, Depends(get_due_count_query)],
) -> DueCountDTO:
    return await query.handle(user_id)


@router.post("/review-sittings")
async def open_sitting(
    user_id: Annotated[UserId, Depends(require_sign_in)],
    command: Annotated[OpenSittingCommand, Depends(get_open_sitting_command)],
) -> SittingOpenedDTO | SittingResumedDTO | NothingDueDTO:
    return await command.handle(user_id)


@router.get("/review-sittings/{sitting_id}/current-card")
async def current_card(
    sitting_id: UUID,
    user_id: Annotated[UserId, Depends(require_sign_in)],
    query: Annotated[CurrentCardQuery, Depends(get_current_card_query)],
) -> PresentedCardDTO:
    return await query.handle(user_id, SittingId(value=sitting_id))


@router.post("/review-sittings/{sitting_id}/cards/{card_id}/back")
async def reveal_back(
    sitting_id: UUID,
    card_id: UUID,
    user_id: Annotated[UserId, Depends(require_sign_in)],
    command: Annotated[RevealBackCommand, Depends(get_reveal_back_command)],
) -> RevealedCardDTO:
    return await command.handle(
        user_id, SittingId(value=sitting_id), CardId(value=card_id)
    )


@router.get("/review-sittings/{sitting_id}/cards/{card_id}/source")
async def card_source(
    sitting_id: UUID,
    card_id: UUID,
    user_id: Annotated[UserId, Depends(require_sign_in)],
    query: Annotated[CardSourceQuery, Depends(get_card_source_query)],
) -> CardSourceDTO:
    return await query.handle(
        user_id, SittingId(value=sitting_id), CardId(value=card_id)
    )


@router.post("/review-sittings/{sitting_id}/cards/{card_id}/grade")
async def grade_card(
    sitting_id: UUID,
    card_id: UUID,
    body: GradeRequestDTO,
    user_id: Annotated[UserId, Depends(require_sign_in)],
    command: Annotated[GradeCardCommand, Depends(get_grade_card_command)],
) -> GradeAppliedDTO:
    return await command.handle(
        user_id, SittingId(value=sitting_id), CardId(value=card_id), body.grade
    )


@router.post("/review-sittings/{sitting_id}/cards/{card_id}/rejection", status_code=204)
async def reject_card(
    sitting_id: UUID,
    card_id: UUID,
    user_id: Annotated[UserId, Depends(require_sign_in)],
    command: Annotated[RejectCardCommand, Depends(get_reject_card_command)],
) -> None:
    await command.handle(user_id, SittingId(value=sitting_id), CardId(value=card_id))
