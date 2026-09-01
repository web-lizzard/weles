import copy
from uuid import UUID

from domain.capture.tag import Tag
from domain.capture.value_objects import TagId


class InMemoryTagRepository:
    def __init__(self) -> None:
        self._tags: dict[UUID, Tag] = {}

    async def add(self, tag: Tag) -> None:
        self._tags[tag.id.value] = tag

    async def get(self, tag_id: TagId) -> Tag | None:
        return self._tags.get(tag_id.value)

    async def candidates(self) -> list[Tag]:
        raise NotImplementedError

    def snapshot(self) -> dict[UUID, Tag]:
        return copy.deepcopy(self._tags)

    def restore(self, snapshot: dict[UUID, Tag]) -> None:
        self._tags = copy.deepcopy(snapshot)
