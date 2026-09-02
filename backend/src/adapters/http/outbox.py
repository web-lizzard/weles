from typing import Annotated

from fastapi import APIRouter, Depends

from adapters.compose import get_outbox_envelope_query
from application.shared.outbox.dto import OutboxEnvelopeDTO
from application.shared.outbox.queries.envelopes import OutboxEnvelopeQueryPort

router = APIRouter()


@router.get("/_outbox")
async def list_outbox_envelopes(
    query: Annotated[OutboxEnvelopeQueryPort, Depends(get_outbox_envelope_query)],
) -> list[OutboxEnvelopeDTO]:
    return await query.list_envelopes()
