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
        target: Embedding,
        candidates: Sequence[VocabularyEntryT],
    ) -> VocabularyMatch[VocabularyEntryT] | None:
        matches = [
            VocabularyMatch(entry=candidate, score=score)
            for candidate in candidates
            if (score := target.cosine_similarity(candidate.embedding)).value
            >= self.threshold.value
        ]
        if not matches:
            return None
        return min(
            matches,
            key=lambda match: (-match.score.value, match.entry.created_at),
        )
