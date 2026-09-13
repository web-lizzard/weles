from typing import Protocol

from domain.distill.card_factory import CardFactory


class DistillDeps(Protocol):
    """Collaborators a distill flow action may reach for. No unit of work and
    no repository: a run persists nothing until the command reads its cards
    off the finished context."""

    @property
    def card_factory(self) -> CardFactory: ...
