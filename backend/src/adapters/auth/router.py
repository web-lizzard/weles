# pyright: reportUnusedParameter=false
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from adapters.auth.authenticator import Authenticator
from adapters.auth.compose import get_authenticator, get_sign_in_verifier
from adapters.auth.dto import (
    RegisterRequestDTO,
    RegisterResponseDTO,
    SignInRequestDTO,
    SignInResponseDTO,
)
from adapters.auth.ports import SignInVerifier
from domain.shared.identity.model import UserId

router = APIRouter(prefix="/auth")

# auto_error=False: a missing header must fail as `sign_in_required` (401),
# not as FastAPI's own 403, so every unsigned caller sees one refusal.
sign_in_scheme = HTTPBearer(auto_error=False)


async def require_sign_in(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(sign_in_scheme)
    ],
    verifier: Annotated[SignInVerifier, Depends(get_sign_in_verifier)],
) -> UserId:
    """The sign-in gate: no credentials -> `SignInRequiredError`; otherwise
    verifier.verify(credentials.credentials).

    Reads no store and calls no LLM before refusing (FR-009). Returns the
    `UserId`; S-01 routes drop it, S-04 hands it to handlers.
    """
    ...


@router.post("/register", status_code=201)
async def register(
    body: RegisterRequestDTO,
    authenticator: Annotated[Authenticator, Depends(get_authenticator)],
) -> RegisterResponseDTO:
    """EmailAddress.parse(body.email), Password(body.password) ->
    authenticator.register."""
    ...


@router.post("/sign-in")
async def sign_in(
    body: SignInRequestDTO,
    authenticator: Annotated[Authenticator, Depends(get_authenticator)],
) -> SignInResponseDTO:
    """EmailAddress.parse(body.email), Password(body.password) ->
    authenticator.sign_in. An unparseable email is `InvalidCredentialsError`,
    not `InvalidEmailAddressError`: sign-in never explains a refusal."""
    ...
