from collections.abc import Callable

import pytest

from domain.distill.exceptions import (
    CardSideTooLongError,
    EmptyAnchorError,
    EmptyCardSideError,
)
from domain.distill.value_objects import (
    ANCHOR_MAX_LENGTH,
    CARD_SIDE_MAX_LENGTH,
    Anchor,
    CardLengthPolicy,
    CardSide,
)


def _build_card_side(text: str) -> object:
    return CardSide(value=text)


def _build_anchor(text: str) -> object:
    return Anchor(quote=text)


def test_card_side_and_anchor_store_canonical_stripped_text() -> None:
    side = CardSide(value="  What establishes a connection?  ")
    anchor = Anchor(quote="  Connections are established via handshakes.  ")

    assert side.value == "What establishes a connection?"
    assert anchor.quote == "Connections are established via handshakes."


@pytest.mark.parametrize(
    ("build", "expected_error"),
    [
        pytest.param(_build_card_side, EmptyCardSideError, id="card_side"),
        pytest.param(_build_anchor, EmptyAnchorError, id="anchor"),
    ],
)
def test_text_empty_after_strip_is_rejected(
    build: Callable[[str], object],
    expected_error: type[Exception],
) -> None:
    with pytest.raises(expected_error):
        _ = build("   ")


@pytest.mark.parametrize(
    ("build", "max_length"),
    [
        pytest.param(_build_card_side, CARD_SIDE_MAX_LENGTH, id="card_side"),
        pytest.param(_build_anchor, ANCHOR_MAX_LENGTH, id="anchor"),
    ],
)
def test_text_past_the_absolute_bound_is_rejected(
    build: Callable[[str], object],
    max_length: int,
) -> None:
    with pytest.raises(CardSideTooLongError):
        _ = build("a" * (max_length + 1))


def test_breach_returns_none_when_both_sides_fit_the_policy() -> None:
    policy = CardLengthPolicy(front_max=10, back_max=20)

    breach = policy.breach(CardSide(value="a" * 10), CardSide(value="b" * 20))

    assert breach is None


@pytest.mark.parametrize(
    ("front_length", "back_length", "expected_detail"),
    [
        pytest.param(11, 20, "front exceeds front_max=10", id="front_only"),
        pytest.param(10, 21, "back exceeds back_max=20", id="back_only"),
        pytest.param(11, 21, "front exceeds front_max=10", id="front_wins_over_back"),
    ],
)
def test_breach_names_the_first_side_that_exceeds_its_bound(
    front_length: int,
    back_length: int,
    expected_detail: str,
) -> None:
    policy = CardLengthPolicy(front_max=10, back_max=20)

    breach = policy.breach(
        CardSide(value="a" * front_length),
        CardSide(value="b" * back_length),
    )

    assert breach == expected_detail
