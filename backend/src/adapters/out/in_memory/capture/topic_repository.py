import copy
from uuid import UUID

from domain.capture.topic import Topic
from domain.capture.value_objects import TopicId


class InMemoryTopicRepository:
    def __init__(self) -> None:
        self._topics: dict[UUID, Topic] = {}

    async def add(self, topic: Topic) -> None:
        self._topics[topic.id.value] = topic

    async def get(self, topic_id: TopicId) -> Topic | None:
        return self._topics.get(topic_id.value)

    async def candidates(self) -> list[Topic]:
        return list(self._topics.values())

    def snapshot(self) -> dict[UUID, Topic]:
        return copy.deepcopy(self._topics)

    def restore(self, snapshot: dict[UUID, Topic]) -> None:
        self._topics = copy.deepcopy(snapshot)
