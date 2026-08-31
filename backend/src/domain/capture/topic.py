from datetime import datetime

from pydantic import BaseModel

from domain.capture.value_objects import Embedding, Label, TopicId


class Topic(BaseModel):
    id: TopicId
    label: Label
    embedding: Embedding
    created_at: datetime

    @classmethod
    def mint(cls, _label: Label, _embedding: Embedding) -> "Topic":
        raise NotImplementedError
