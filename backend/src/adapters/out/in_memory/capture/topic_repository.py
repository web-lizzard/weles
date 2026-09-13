import copy
from uuid import UUID

from adapters.out.in_memory.capture.similarity import cosine_similarity
from domain.capture.topic import Topic
from domain.capture.value_objects import Embedding, TopicId
from domain.capture.vocabulary_match import VocabularyMatch


class InMemoryTopicRepository:
    def __init__(self) -> None:
        self._topics: dict[UUID, Topic] = {}

    async def add(self, topic: Topic) -> None:
        self._topics[topic.id.value] = topic

    async def get(self, topic_id: TopicId) -> Topic | None:
        return self._topics.get(topic_id.value)

    async def nearest(self, embedding: Embedding) -> VocabularyMatch[Topic] | None:
        matches: list[VocabularyMatch[Topic]] = []
        for topic in self._topics.values():
            if topic.embedding.model != embedding.model:
                continue
            if len(topic.embedding.values) != len(embedding.values):
                continue
            score = cosine_similarity(embedding, topic.embedding)
            matches.append(VocabularyMatch(entry=topic, score=score))
        if not matches:
            return None
        return min(
            matches,
            key=lambda match: (-match.score.value, match.entry.created_at),
        )

    def snapshot(self) -> dict[UUID, Topic]:
        return copy.deepcopy(self._topics)

    def restore(self, snapshot: dict[UUID, Topic]) -> None:
        self._topics = copy.deepcopy(snapshot)
