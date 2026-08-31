from datetime import datetime

from pydantic import BaseModel

from domain.capture.value_objects import Embedding, Label, TagId


class Tag(BaseModel):
    id: TagId
    label: Label
    embedding: Embedding
    created_at: datetime

    @classmethod
    def mint(cls, _label: Label, _embedding: Embedding) -> "Tag":
        raise NotImplementedError
