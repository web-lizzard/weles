import asyncio

from adapters.out.in_memory.capture.tag_repository import InMemoryTagRepository
from adapters.out.in_memory.capture.topic_repository import InMemoryTopicRepository
from domain.capture.exceptions import NoteVocabularyIncompleteError
from domain.capture.note import Note
from domain.capture.note_vocabulary import NoteVocabulary
from domain.capture.tag import Tag


class InMemoryNoteVocabularyRepository:
    def __init__(
        self,
        topics: InMemoryTopicRepository,
        tags: InMemoryTagRepository,
    ) -> None:
        self._topics: InMemoryTopicRepository = topics
        self._tags: InMemoryTagRepository = tags

    async def resolve(self, note: Note) -> NoteVocabulary:
        topic = await self._topics.get(note.topic_id)
        if topic is None:
            raise NoteVocabularyIncompleteError

        tag_results = await asyncio.gather(
            *[self._tags.get(tag_id) for tag_id in note.tag_ids]
        )
        tags: list[Tag] = []
        for tag in tag_results:
            if tag is None:
                raise NoteVocabularyIncompleteError
            tags.append(tag)

        return NoteVocabulary(topic=topic, tags=tags)
