from datetime import UTC, datetime

from pydantic import BaseModel

from domain.capture.value_objects import Embedding, Label, TopicId


class Topic(BaseModel):
    id: TopicId
    label: Label
    embedding: Embedding
    created_at: datetime

    @classmethod
    def mint(cls, label: Label, embedding: Embedding) -> "Topic":
        return cls(
            id=TopicId.new(),
            label=label,
            embedding=embedding,
            created_at=datetime.now(UTC),
        )
