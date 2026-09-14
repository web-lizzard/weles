import pytest
from pydantic import SecretStr

from adapters.auth.model import Password, PasswordHash
from adapters.auth.passwords import PasswordHasher


async def test_password_hasher_verify_recognizes_only_the_hashed_password() -> None:
    hasher = PasswordHasher()
    correct = Password(value=SecretStr("correct horse battery staple"))
    wrong = Password(value=SecretStr("wrong horse battery staple"))

    password_hash = await hasher.hash(correct)

    assert await hasher.verify(correct, password_hash) is True
    assert await hasher.verify(wrong, password_hash) is False


@pytest.mark.parametrize("hash_value", ["not-a-real-hash", ""])
async def test_password_hasher_verify_returns_false_for_an_unparseable_hash(
    hash_value: str,
) -> None:
    hasher = PasswordHasher()
    password = Password(value=SecretStr("whatever password"))

    result = await hasher.verify(password, PasswordHash(value=hash_value))

    assert result is False
