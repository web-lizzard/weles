from datetime import UTC, datetime

import pytest
from pydantic import SecretStr

from adapters.auth.exceptions import InvalidEmailAddressError, PasswordTooShortError
from adapters.auth.model import (
    Account,
    EmailAddress,
    Password,
    PasswordHash,
    PasswordPolicy,
)


def test_email_address_parse_case_folds_and_strips_whitespace() -> None:
    email = EmailAddress.parse("  Alice.Example@DOMAIN.com  ")

    assert email.value == "alice.example@domain.com"


def test_email_address_parse_raises_invalid_email_address_error_for_bad_syntax() -> (
    None
):
    with pytest.raises(InvalidEmailAddressError):
        _ = EmailAddress.parse("not-an-email")


def test_password_policy_admit_raises_password_too_short_error_below_minimum() -> None:
    policy = PasswordPolicy(min_length=8)

    with pytest.raises(PasswordTooShortError):
        policy.admit(Password(value=SecretStr("1234567")))


def test_account_register_assigns_fresh_user_id_and_current_created_at() -> None:
    email = EmailAddress.parse("alice@example.com")
    password_hash = PasswordHash(value="opaque-hash")

    before = datetime.now(UTC)
    first = Account.register(email=email, password_hash=password_hash)
    second = Account.register(email=email, password_hash=password_hash)
    after = datetime.now(UTC)

    assert before <= first.created_at <= after
    assert first.id != second.id
