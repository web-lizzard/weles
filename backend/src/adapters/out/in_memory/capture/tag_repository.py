import copy
from uuid import UUID

from adapters.out.in_memory.capture.similarity import cosine_similarity
from domain.capture.tag import Tag
from domain.capture.value_objects import Embedding, TagId
from domain.capture.vocabulary_match import VocabularyMatch


class InMemoryTagRepository:
    def __init__(self) -> None:
        self._tags: dict[UUID, Tag] = {}

    async def add(self, tag: Tag) -> None:
        self._tags[tag.id.value] = tag

    async def get(self, tag_id: TagId) -> Tag | None:
        return self._tags.get(tag_id.value)

    async def nearest(self, embedding: Embedding) -> VocabularyMatch[Tag] | None:
        matches: list[VocabularyMatch[Tag]] = []
        for tag in self._tags.values():
            if tag.embedding.model != embedding.model:
                continue
            if len(tag.embedding.values) != len(embedding.values):
                continue
            score = cosine_similarity(embedding, tag.embedding)
            matches.append(VocabularyMatch(entry=tag, score=score))
        if not matches:
            return None
        return min(
            matches,
            key=lambda match: (-match.score.value, match.entry.created_at),
        )

    def snapshot(self) -> dict[UUID, Tag]:
        return copy.deepcopy(self._tags)

    def restore(self, snapshot: dict[UUID, Tag]) -> None:
        self._tags = copy.deepcopy(snapshot)
