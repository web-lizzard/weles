import copy
from uuid import UUID

from domain.capture.tag import Tag
from domain.capture.value_objects import TagId


class InMemoryTagRepository:
    def __init__(self) -> None:
        self._tags: dict[UUID, Tag] = {}

    async def add(self, _tag: Tag) -> None:
        raise NotImplementedError

    async def get(self, _tag_id: TagId) -> Tag | None:
        raise NotImplementedError

    def snapshot(self) -> dict[UUID, Tag]:
        return copy.deepcopy(self._tags)

    def restore(self, snapshot: dict[UUID, Tag]) -> None:
        self._tags = copy.deepcopy(snapshot)
