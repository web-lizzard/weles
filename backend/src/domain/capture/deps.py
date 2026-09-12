from dataclasses import dataclass
from typing import Protocol


class CaptureDeps(Protocol):
    """Collaborators a capture graph action may reach for.

    Expanded in a later phase; actions ignore this set until drafting work moves
    onto the graph.
    """


@dataclass(frozen=True)
class NullCaptureDeps:
    """Placeholder until the command assembles real repositories for a turn."""


NULL_CAPTURE_DEPS: CaptureDeps = NullCaptureDeps()
