import copy
from uuid import UUID

from domain.capture.topic import Topic
from domain.capture.value_objects import TopicId


class InMemoryTopicRepository:
    def __init__(self) -> None:
        self._topics: dict[UUID, Topic] = {}

    async def add(self, _topic: Topic) -> None:
        raise NotImplementedError

    async def get(self, _topic_id: TopicId) -> Topic | None:
        raise NotImplementedError

    def snapshot(self) -> dict[UUID, Topic]:
        return copy.deepcopy(self._topics)

    def restore(self, snapshot: dict[UUID, Topic]) -> None:
        self._topics = copy.deepcopy(snapshot)
