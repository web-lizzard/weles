from pydantic import BaseModel

from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.value_objects import SimilarityScore


class VocabularyMatch[VocabularyEntryT: (Topic, Tag)](BaseModel, frozen=True):
    entry: VocabularyEntryT
    score: SimilarityScore
