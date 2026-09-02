from adapters.out.in_memory.capture.tag_repository import InMemoryTagRepository
from adapters.out.in_memory.capture.topic_repository import InMemoryTopicRepository
from domain.capture.note import Note
from domain.capture.note_vocabulary import NoteVocabulary


class InMemoryNoteVocabularyRepository:
    def __init__(
        self,
        topics: InMemoryTopicRepository,
        tags: InMemoryTagRepository,
    ) -> None:
        self._topics: InMemoryTopicRepository = topics
        self._tags: InMemoryTagRepository = tags

    async def resolve(self, _note: Note) -> NoteVocabulary:
        raise NotImplementedError
