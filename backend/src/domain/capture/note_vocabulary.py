from pydantic import BaseModel

from domain.capture.tag import Tag
from domain.capture.topic import Topic


class NoteVocabulary(BaseModel, frozen=True):
    topic: Topic
    tags: list[Tag]
