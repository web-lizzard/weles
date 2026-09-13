from pydantic import BaseModel

from domain.distill.value_objects import NoteContent


class ThresholdTier(BaseModel, frozen=True):
    """Notes up to `max_length` characters regenerate when the accepted share
    of the first round falls below `min_accepted_share`. `None` is the open
    top tier."""

    max_length: int | None
    min_accepted_share: float


class RegenerationPolicy(BaseModel, frozen=True):
    """When a first round is not good enough to end generation.

    Invariant: tiers ascend by `max_length` and exactly the last one is open,
    so every note length falls into one tier. The tier values are heuristics,
    supplied by composition like `CardLengthPolicy`.
    """

    tiers: tuple[ThresholdTier, ...]

    def regenerate(self, content: NoteContent, accepted: int, proposed: int) -> bool:
        """Whether the round regenerates: `accepted / proposed` is below the
        tier's share for this note's length.

        `proposed` counts every proposal of the round, including those
        discarded before review. A round with no proposals regenerates — its
        share counts as below any threshold.
        """
        _ = content, accepted, proposed
        raise NotImplementedError
