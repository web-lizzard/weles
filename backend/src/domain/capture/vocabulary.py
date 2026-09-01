from collections.abc import Sequence

from pydantic import BaseModel

from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.value_objects import Embedding, SimilarityScore


class VocabularyMatch[VocabularyEntryT: (Topic, Tag)](BaseModel, frozen=True):
    entry: VocabularyEntryT
    score: SimilarityScore


class MatchCriteria(BaseModel, frozen=True):
    threshold: SimilarityScore

    def best_match[VocabularyEntryT: (Topic, Tag)](
        self,
        target: Embedding,  # pyright: ignore[reportUnusedParameter]
        candidates: Sequence[VocabularyEntryT],  # pyright: ignore[reportUnusedParameter]
    ) -> VocabularyMatch[VocabularyEntryT] | None:
        raise NotImplementedError
