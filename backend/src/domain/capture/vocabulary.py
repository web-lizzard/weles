from collections.abc import Sequence

from pydantic import BaseModel

from domain.capture.exceptions import EmbeddingDimensionMismatchError
from domain.capture.ports import EmbeddingPort, TagRepository, TopicRepository
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.value_objects import Embedding, Label, SimilarityScore


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
        matches: list[VocabularyMatch[VocabularyEntryT]] = []
        for candidate in candidates:
            try:
                score = target.cosine_similarity(candidate.embedding)
            except EmbeddingDimensionMismatchError:
                continue
            if score.value >= self.threshold.value:
                matches.append(VocabularyMatch(entry=candidate, score=score))
        if not matches:
            return None
        return min(
            matches,
            key=lambda match: (-match.score.value, match.entry.created_at),
        )


class ResolvedTopic(BaseModel, frozen=True):
    topic: Topic
    reused: bool


class ResolvedTag(BaseModel, frozen=True):
    tag: Tag
    reused: bool


class VocabularyResolver:
    def __init__(self, embedding: EmbeddingPort, criteria: MatchCriteria) -> None:
        self._embedding: EmbeddingPort = embedding
        self._criteria: MatchCriteria = criteria

    async def resolve_topic(
        self, label: Label, topics: TopicRepository
    ) -> ResolvedTopic:
        embedding, match = await self._best_match(label, await topics.candidates())
        if match is not None:
            return ResolvedTopic(topic=match.entry, reused=True)
        topic = Topic.mint(label, embedding)
        await topics.add(topic)
        return ResolvedTopic(topic=topic, reused=False)

    async def resolve_tag(self, label: Label, tags: TagRepository) -> ResolvedTag:
        embedding, match = await self._best_match(label, await tags.candidates())
        if match is not None:
            return ResolvedTag(tag=match.entry, reused=True)
        tag = Tag.mint(label, embedding)
        await tags.add(tag)
        return ResolvedTag(tag=tag, reused=False)

    async def _best_match[VocabularyEntryT: (Topic, Tag)](
        self, label: Label, candidates: Sequence[VocabularyEntryT]
    ) -> tuple[Embedding, VocabularyMatch[VocabularyEntryT] | None]:
        embedding = await self._embedding.embed(label.value)
        return embedding, self._criteria.best_match(embedding, candidates)
