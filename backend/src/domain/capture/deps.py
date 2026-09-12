from dataclasses import dataclass
from typing import Protocol, cast

from domain.capture.ports import (
    MessageRepository,
    NoteRepository,
    NoteVocabularyRepository,
    TagRepository,
    TopicRepository,
)
from domain.capture.vocabulary import VocabularyResolver


class CaptureDeps(Protocol):
    """Collaborators a capture graph action may reach for.

    Every member is a domain repository port or the vocabulary resolver — no
    unit of work and no commit, so an action cannot reach the transaction
    boundary.
    """

    @property
    def messages(self) -> MessageRepository: ...

    @property
    def notes(self) -> NoteRepository: ...

    @property
    def topics(self) -> TopicRepository: ...

    @property
    def tags(self) -> TagRepository: ...

    @property
    def note_vocabulary(self) -> NoteVocabularyRepository: ...

    @property
    def vocabulary(self) -> VocabularyResolver: ...


@dataclass(frozen=True)
class NullCaptureDeps:
    """Placeholder until the command assembles real repositories for a turn."""


NULL_CAPTURE_DEPS: CaptureDeps = cast(CaptureDeps, cast(object, NullCaptureDeps()))
