import json
from typing import ClassVar

import pytest
from fastapi import Request

from adapters.http.errors import EXCEPTION_STATUS_MAP, core_exception_handler
from domain.exceptions import CoreException


@pytest.mark.parametrize(
    ("code", "expected_status"),
    [
        ("note_not_draft", 409),
        ("note_session_mismatch", 409),
        ("session_note_missing", 409),
        ("note_not_found", 404),
        ("tag_not_on_note", 409),
    ],
)
def test_capture_approval_exception_codes_map_to_contract_status(
    code: str, expected_status: int
) -> None:
    assert EXCEPTION_STATUS_MAP.get(code) == expected_status


def test_every_core_exception_code_is_mapped_to_a_status() -> None:
    for subclass in _all_subclasses(CoreException):
        assert subclass.code() in EXCEPTION_STATUS_MAP


def test_no_two_core_exception_subclasses_collide_on_code() -> None:
    codes = [subclass.code() for subclass in _all_subclasses(CoreException)]
    assert len(codes) == len(set(codes))


@pytest.mark.asyncio
async def test_core_exception_handler_maps_not_found_error_to_404() -> None:
    class NotFoundError(CoreException):
        pass

    request = Request(scope={"type": "http"})
    exc = NotFoundError("missing")

    response = await core_exception_handler(request, exc)

    assert response.status_code == 404
    assert json.loads(bytes(response.body))["code"] == "not_found"


@pytest.mark.asyncio
async def test_core_exception_handler_includes_detail_message() -> None:
    """core_exception_handler must return detail equal to str(exc)."""

    class NotFoundError(CoreException):
        pass

    request = Request(scope={"type": "http"})
    exc = NotFoundError("missing resource")

    response = await core_exception_handler(request, exc)

    assert json.loads(bytes(response.body))["detail"] == "missing resource"


@pytest.mark.asyncio
async def test_core_exception_handler_falls_back_to_500_for_unmapped_code() -> None:
    """Unmapped exception code falls back to HTTP 500."""

    class UnmappedError(CoreException):
        _code: ClassVar[str] = "unmapped_for_test_only"

    request = Request(scope={"type": "http"})
    exc = UnmappedError("unexpected failure")

    response = await core_exception_handler(request, exc)

    assert response.status_code == 500
    assert json.loads(bytes(response.body))["code"] == "unmapped_for_test_only"


def _all_subclasses(cls: type[CoreException]) -> set[type[CoreException]]:
    subclasses: set[type[CoreException]] = set()
    for subclass in cls.__subclasses__():
        subclasses.add(subclass)
        subclasses.update(_all_subclasses(subclass))
    return subclasses
