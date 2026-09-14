from datetime import UTC, datetime

from pydantic import BaseModel

from domain.capture.value_objects import Embedding, Label, TagId
from domain.shared.identity.model import UserId


class Tag(BaseModel):
    id: TagId
    owner_id: UserId
    label: Label
    embedding: Embedding
    created_at: datetime

    @classmethod
    def mint(cls, owner: UserId, label: Label, embedding: Embedding) -> "Tag":
        return cls(
            id=TagId.new(),
            owner_id=owner,
            label=label,
            embedding=embedding,
            created_at=datetime.now(UTC),
        )
