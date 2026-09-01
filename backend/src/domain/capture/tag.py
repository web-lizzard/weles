from datetime import UTC, datetime

from pydantic import BaseModel

from domain.capture.value_objects import Embedding, Label, TagId


class Tag(BaseModel):
    id: TagId
    label: Label
    embedding: Embedding
    created_at: datetime

    @classmethod
    def mint(cls, label: Label, embedding: Embedding) -> "Tag":
        return cls(
            id=TagId.new(),
            label=label,
            embedding=embedding,
            created_at=datetime.now(UTC),
        )
