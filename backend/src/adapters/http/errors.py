from fastapi import Request
from fastapi.responses import JSONResponse

from domain.exceptions import CoreException

EXCEPTION_STATUS_MAP: dict[str, int] = {}


async def core_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, CoreException)
    raise NotImplementedError
