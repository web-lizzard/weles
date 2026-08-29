import json

import pytest
from fastapi import Request

from adapters.http.errors import EXCEPTION_STATUS_MAP, core_exception_handler
from domain.exceptions import CoreException


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


def _all_subclasses(cls: type[CoreException]) -> set[type[CoreException]]:
    subclasses: set[type[CoreException]] = set()
    for subclass in cls.__subclasses__():
        subclasses.add(subclass)
        subclasses.update(_all_subclasses(subclass))
    return subclasses
