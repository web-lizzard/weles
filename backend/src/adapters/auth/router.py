# pyright: reportUnusedParameter=false
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from adapters.auth.authenticator import Authenticator
from adapters.auth.compose import (
    get_authenticator,
    get_sign_in_verifier,
    get_trusted_proxy_addresses,
)
from adapters.auth.dto import (
    RegisterRequestDTO,
    RegisterResponseDTO,
    SignInRequestDTO,
    SignInResponseDTO,
)
from adapters.auth.exceptions import (
    InvalidCredentialsError,
    InvalidEmailAddressError,
    SignInRequiredError,
)
from adapters.auth.model import AttemptSource, EmailAddress, Password
from adapters.auth.ports import SignInVerifier
from adapters.auth.source import resolve_attempt_source
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
    if credentials is None:
        raise SignInRequiredError
    return await verifier.verify(credentials.credentials)


async def attempt_source(
    request: Request,
    trusted_proxies: Annotated[frozenset[str], Depends(get_trusted_proxy_addresses)],
) -> AttemptSource:
    """Who is making this request, for attempt limiting.

    Delegates to `resolve_attempt_source`, which this phase still resolves as
    the connection's peer host regardless of `X-Forwarded-For`. Phase 6 makes
    the resolver trust proxy headers from `trusted_proxies`.
    """
    host = request.client.host if request.client is not None else None
    forwarded_for = request.headers.get("x-forwarded-for")
    return resolve_attempt_source(host, forwarded_for, trusted_proxies)


@router.post("/register", status_code=201)
async def register(
    body: RegisterRequestDTO,
    authenticator: Annotated[Authenticator, Depends(get_authenticator)],
    source: Annotated[AttemptSource, Depends(attempt_source)],
) -> RegisterResponseDTO:
    """EmailAddress.parse(body.email), Password(body.password) ->
    authenticator.register."""
    email = EmailAddress.parse(body.email)
    password = Password(value=body.password)
    user_id = await authenticator.register(email, password, source)
    return RegisterResponseDTO(user_id=user_id.value)


@router.post("/sign-in")
async def sign_in(
    body: SignInRequestDTO,
    authenticator: Annotated[Authenticator, Depends(get_authenticator)],
    source: Annotated[AttemptSource, Depends(attempt_source)],
) -> SignInResponseDTO:
    """EmailAddress.parse(body.email), Password(body.password) ->
    authenticator.sign_in. An unparseable email is `InvalidCredentialsError`,
    not `InvalidEmailAddressError`: sign-in never explains a refusal."""
    try:
        email = EmailAddress.parse(body.email)
    except InvalidEmailAddressError:
        raise InvalidCredentialsError from None
    password = Password(value=body.password)
    issued = await authenticator.sign_in(email, password, source)
    return SignInResponseDTO(
        access_token=issued.token,
        expires_at=issued.expires_at,
    )
