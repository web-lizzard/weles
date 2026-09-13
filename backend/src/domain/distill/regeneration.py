from pydantic import BaseModel, model_validator

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

    @model_validator(mode="after")
    def _tiers_ascend_and_end_open(self) -> "RegenerationPolicy":
        if not self.tiers:
            raise ValueError("regeneration policy needs at least one tier")
        *closed, last = self.tiers
        if last.max_length is not None:
            raise ValueError("last tier must be open")
        previous: int | None = None
        for tier in closed:
            ceiling = tier.max_length
            if ceiling is None:
                raise ValueError("only the last tier may be open")
            if previous is not None and ceiling <= previous:
                raise ValueError("finite tier ceilings must ascend")
            previous = ceiling
        return self

    def regenerate(self, content: NoteContent, accepted: int, proposed: int) -> bool:
        """Whether the round regenerates: `accepted / proposed` is below the
        tier's share for this note's length.

        `proposed` counts every proposal of the round, including those
        discarded before review. A round with no proposals regenerates — its
        share counts as below any threshold.
        """
        length = len(content.value)
        for tier in self.tiers:
            if tier.max_length is None or tier.max_length >= length:
                return proposed == 0 or accepted / proposed < tier.min_accepted_share
        raise ValueError("no tier covers this note length")
