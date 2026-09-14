from datetime import UTC, datetime

from pydantic import BaseModel

from domain.capture.value_objects import Embedding, Label, TopicId
from domain.shared.identity.model import UserId


class Topic(BaseModel):
    id: TopicId
    owner_id: UserId
    label: Label
    embedding: Embedding
    created_at: datetime

    @classmethod
    def mint(cls, owner: UserId, label: Label, embedding: Embedding) -> "Topic":
        return cls(
            id=TopicId.new(),
            owner_id=owner,
            label=label,
            embedding=embedding,
            created_at=datetime.now(UTC),
        )
