import pytest

from domain.distill.regeneration import RegenerationPolicy, ThresholdTier
from domain.distill.value_objects import NoteContent


def _policy() -> RegenerationPolicy:
    return RegenerationPolicy(
        tiers=(
            ThresholdTier(max_length=1500, min_accepted_share=0.5),
            ThresholdTier(max_length=6000, min_accepted_share=0.6),
            ThresholdTier(max_length=None, min_accepted_share=0.7),
        )
    )


@pytest.mark.parametrize(
    ("length", "accepted", "proposed", "expected"),
    [
        pytest.param(1500, 1, 2, False, id="short_ceiling_share_on_the_line"),
        pytest.param(1500, 0, 2, True, id="short_ceiling_share_below_the_line"),
        pytest.param(1501, 1, 2, True, id="mid_tier_just_past_short_ceiling"),
        pytest.param(6000, 3, 5, False, id="mid_ceiling_share_on_the_line"),
        pytest.param(6001, 3, 5, True, id="open_tier_just_past_mid_ceiling"),
    ],
)
def test_regeneration_uses_the_first_tier_whose_ceiling_covers_the_note(
    length: int,
    accepted: int,
    proposed: int,
    expected: bool,
) -> None:
    content = NoteContent(value="a" * length)

    assert _policy().regenerate(content, accepted, proposed) is expected


def test_a_round_with_no_proposals_regenerates() -> None:
    content = NoteContent(value="a")

    assert _policy().regenerate(content, accepted=0, proposed=0) is True


@pytest.mark.parametrize(
    "tiers",
    [
        pytest.param(
            (
                ThresholdTier(max_length=1500, min_accepted_share=0.5),
                ThresholdTier(max_length=6000, min_accepted_share=0.6),
            ),
            id="last_tier_is_closed",
        ),
        pytest.param(
            (
                ThresholdTier(max_length=None, min_accepted_share=0.7),
                ThresholdTier(max_length=1500, min_accepted_share=0.5),
            ),
            id="open_tier_is_not_last",
        ),
        pytest.param(
            (
                ThresholdTier(max_length=6000, min_accepted_share=0.6),
                ThresholdTier(max_length=1500, min_accepted_share=0.5),
                ThresholdTier(max_length=None, min_accepted_share=0.7),
            ),
            id="finite_ceilings_are_not_ascending",
        ),
    ],
)
def test_malformed_tier_lists_are_refused(
    tiers: tuple[ThresholdTier, ...],
) -> None:
    with pytest.raises(ValueError):
        _ = RegenerationPolicy(tiers=tiers)
