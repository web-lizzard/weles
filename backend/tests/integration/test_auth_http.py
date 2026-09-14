"""HTTP contracts for registration, sign-in, and the sign-in gate."""

from collections.abc import Iterator
from datetime import timedelta
from typing import cast

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from adapters.auth.authenticator import Authenticator
from adapters.auth.compose import (
    get_authenticator,
    get_sign_in_verifier,
    get_trusted_proxy_addresses,
)
from adapters.auth.in_memory_account_store import InMemoryAccountStore
from adapters.auth.in_memory_attempt_ledger import InMemoryAttemptLedger
from adapters.auth.model import (
    DEFAULT_ATTEMPT_LIMITS,
    AttemptLimit,
    AttemptLimits,
    PasswordPolicy,
    SigningSecret,
    SignInLifetime,
)
from adapters.auth.passwords import PasswordHasher
from adapters.auth.tokens import SignInTokens
from adapters.compose import get_list_notes_query
from adapters.out.in_memory.distill.card_repository import InMemoryCardRepository
from adapters.out.in_memory.distill.list_notes_query import (
    InMemoryListNotesQueryAdapter,
)
from adapters.out.in_memory.distill.note_repository import (
    InMemoryNoteRepository as InMemoryDistillNoteRepository,
)
from main import app

_TEST_SIGNING_SECRET = "a" * 32
_VALID_PASSWORD = "long-enough-secret"


def _small_limits(max_attempts: int = 2) -> AttemptLimits:
    limit = AttemptLimit(max_attempts=max_attempts, window=timedelta(minutes=15))
    return AttemptLimits(sign_in=limit, registration=limit)


def _auth_stack(
    limits: AttemptLimits | None = None,
) -> tuple[InMemoryAccountStore, SignInTokens, Authenticator]:
    accounts = InMemoryAccountStore()
    tokens = SignInTokens(
        secret=SigningSecret(value=SecretStr(_TEST_SIGNING_SECRET)),
        lifetime=SignInLifetime(value=timedelta(hours=24)),
        accounts=accounts,
    )
    authenticator = Authenticator(
        accounts=accounts,
        passwords=PasswordHasher(),
        policy=PasswordPolicy(min_length=8),
        issuer=tokens,
        attempts=InMemoryAttemptLedger(limits or DEFAULT_ATTEMPT_LIMITS),
    )
    return accounts, tokens, authenticator


@pytest.fixture
def auth_http_client() -> Iterator[TestClient]:
    _accounts, tokens, authenticator = _auth_stack()
    notes = InMemoryDistillNoteRepository()
    cards = InMemoryCardRepository()
    list_notes = InMemoryListNotesQueryAdapter(notes, cards)
    app.dependency_overrides[get_authenticator] = lambda: authenticator
    app.dependency_overrides[get_sign_in_verifier] = lambda: tokens
    app.dependency_overrides[get_list_notes_query] = lambda: list_notes
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def limited_auth_client() -> Iterator[TestClient]:
    _accounts, tokens, authenticator = _auth_stack(limits=_small_limits())
    app.dependency_overrides[get_authenticator] = lambda: authenticator
    app.dependency_overrides[get_sign_in_verifier] = lambda: tokens
    app.dependency_overrides[get_trusted_proxy_addresses] = lambda: frozenset(
        {"testclient"}
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    app.dependency_overrides.clear()


def _wrong_sign_in_status(client: TestClient, email: str, forwarded_for: str) -> int:
    return client.post(
        "/auth/sign-in",
        json={"email": email, "password": "wrong-but-long-enough"},
        headers={"x-forwarded-for": forwarded_for},
    ).status_code


def _register(client: TestClient, email: str, password: str = _VALID_PASSWORD) -> None:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 201


def _sign_in(client: TestClient, email: str, password: str = _VALID_PASSWORD) -> str:
    response = client.post(
        "/auth/sign-in",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    body = cast(dict[str, object], response.json())
    token = body["access_token"]
    assert isinstance(token, str)
    return token


def test_register_then_sign_in_token_passes_gated_route(
    auth_http_client: TestClient,
) -> None:
    email = "person@example.com"
    _register(auth_http_client, email)
    token = _sign_in(auth_http_client, email)

    response = auth_http_client.get(
        "/notes",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_duplicate_registration_different_case_returns_email_already_registered(
    auth_http_client: TestClient,
) -> None:
    _register(auth_http_client, "alice@example.com")

    response = auth_http_client.post(
        "/auth/register",
        json={"email": "ALICE@EXAMPLE.COM", "password": _VALID_PASSWORD},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "email_already_registered"


def test_sign_in_wrong_password_returns_invalid_credentials(
    auth_http_client: TestClient,
) -> None:
    email = "wrong-pass@example.com"
    _register(auth_http_client, email)

    response = auth_http_client.post(
        "/auth/sign-in",
        json={"email": email, "password": "not-the-right-secret"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"


def test_sign_in_unknown_email_returns_invalid_credentials(
    auth_http_client: TestClient,
) -> None:
    response = auth_http_client.post(
        "/auth/sign-in",
        json={"email": "nobody@example.com", "password": _VALID_PASSWORD},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"


def test_gated_route_without_token_returns_sign_in_required_before_notes_query(
    auth_http_client: TestClient,
) -> None:
    def _query_must_not_run() -> object:
        raise AssertionError("gate must refuse before any notes query runs")

    app.dependency_overrides[get_list_notes_query] = _query_must_not_run
    try:
        response = auth_http_client.get("/notes")
    finally:
        del app.dependency_overrides[get_list_notes_query]

    assert response.status_code == 401
    assert response.json()["code"] == "sign_in_required"


def test_gated_route_with_forged_token_returns_sign_in_required_before_notes_query(
    auth_http_client: TestClient,
) -> None:
    def _query_must_not_run() -> object:
        raise AssertionError("gate must refuse before any notes query runs")

    app.dependency_overrides[get_list_notes_query] = _query_must_not_run
    try:
        response = auth_http_client.get(
            "/notes",
            headers={"Authorization": "Bearer not.a.valid.token"},
        )
    finally:
        del app.dependency_overrides[get_list_notes_query]

    assert response.status_code == 401
    assert response.json()["code"] == "sign_in_required"


def test_gated_route_with_token_for_a_deleted_account_returns_account_no_longer_exists(
    auth_http_client: TestClient,
) -> None:
    email = "vanished@example.com"
    _register(auth_http_client, email)
    token = _sign_in(auth_http_client, email)

    stranded = SignInTokens(
        secret=SigningSecret(value=SecretStr(_TEST_SIGNING_SECRET)),
        lifetime=SignInLifetime(value=timedelta(hours=24)),
        accounts=InMemoryAccountStore(),
    )
    app.dependency_overrides[get_sign_in_verifier] = lambda: stranded

    response = auth_http_client.get(
        "/notes",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "account_no_longer_exists"


def test_health_returns_ok_without_token(auth_http_client: TestClient) -> None:
    response = auth_http_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_sign_in_answers_429_with_retry_after_once_failures_reach_the_limit(
    limited_auth_client: TestClient,
) -> None:
    email = "alice@example.com"
    _register(limited_auth_client, email)
    for _ in range(2):
        assert _wrong_sign_in_status(limited_auth_client, email, "198.51.100.1") == 401

    response = limited_auth_client.post(
        "/auth/sign-in",
        json={"email": email, "password": "wrong-but-long-enough"},
        headers={"x-forwarded-for": "198.51.100.1"},
    )

    assert response.status_code == 429
    assert cast(dict[str, object], response.json())["code"] == "too_many_attempts"
    assert int(response.headers["retry-after"]) > 0


def test_registration_beyond_the_limit_answers_429(
    limited_auth_client: TestClient,
) -> None:
    headers = {"x-forwarded-for": "198.51.100.1"}
    for index in range(2):
        assert (
            limited_auth_client.post(
                "/auth/register",
                json={
                    "email": f"alice{index}@example.com",
                    "password": _VALID_PASSWORD,
                },
                headers=headers,
            ).status_code
            == 201
        )

    response = limited_auth_client.post(
        "/auth/register",
        json={"email": "alice2@example.com", "password": _VALID_PASSWORD},
        headers=headers,
    )

    assert response.status_code == 429
    assert cast(dict[str, object], response.json())["code"] == "too_many_attempts"


def test_a_limited_source_does_not_refuse_a_different_forwarded_source(
    limited_auth_client: TestClient,
) -> None:
    email = "alice@example.com"
    _register(limited_auth_client, email)
    for _ in range(2):
        _ = _wrong_sign_in_status(limited_auth_client, email, "198.51.100.1")
    assert _wrong_sign_in_status(limited_auth_client, email, "198.51.100.1") == 429

    assert _wrong_sign_in_status(limited_auth_client, email, "198.51.100.2") == 401
