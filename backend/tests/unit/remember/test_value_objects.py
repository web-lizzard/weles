import pytest

from domain.remember.exceptions import InvalidShowingLimitError
from domain.remember.value_objects import ShowingLimit


@pytest.mark.parametrize("value", [0, -1])
def test_a_showing_limit_below_one_is_refused(value: int) -> None:
    with pytest.raises(InvalidShowingLimitError):
        _ = ShowingLimit(value=value)
