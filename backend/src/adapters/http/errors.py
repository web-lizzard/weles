from fastapi import Request
from fastapi.responses import JSONResponse

from domain.exceptions import CoreException

EXCEPTION_STATUS_MAP: dict[str, int] = {
    "not_found": 404,
    "capture_session_not_found": 404,
    "capture_session_closed": 409,
    "session_topic_already_assigned": 409,
    "empty_session_topic": 422,
    "session_topic_too_long": 422,
    "empty_message_content": 422,
    "message_content_too_long": 422,
    "empty_confidence_point": 422,
    "empty_label": 422,
    "label_too_long": 422,
    "empty_embedding": 422,
    "empty_note_content": 422,
    "note_content_too_long": 422,
    "session_note_already_drafted": 409,
    "draft_topic_missing": 500,
    "similarity_score_out_of_range": 422,
    "embedding_dimension_mismatch": 422,
    "zero_magnitude_embedding": 422,
}


async def core_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, CoreException)
    status_code = EXCEPTION_STATUS_MAP.get(exc.code(), 500)
    content = {"code": exc.code(), "detail": str(exc)}
    return JSONResponse(status_code=status_code, content=content)
