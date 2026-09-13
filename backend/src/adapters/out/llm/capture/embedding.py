from pydantic_ai.embeddings import Embedder
from pydantic_ai.embeddings.settings import EmbeddingSettings

from adapters.out.llm.tracing import observation
from domain.capture.value_objects import Embedding


class OpenRouterEmbeddingAdapter:
    _embedder: Embedder
    _model_name: str
    _dimensions: int | None

    def __init__(
        self, embedder: Embedder, model_name: str, dimensions: int | None = None
    ) -> None:
        self._embedder = embedder
        self._model_name = model_name
        self._dimensions = dimensions

    async def embed(self, text: str) -> Embedding:
        with observation(
            "embedding", observation_type="embedding", input_value=text
        ) as recorder:
            recorder.record_model(self._model_name)
            settings = (
                EmbeddingSettings(dimensions=self._dimensions)
                if self._dimensions is not None
                else None
            )
            result = await self._embedder.embed_query(text, settings=settings)
            values = tuple(result.embeddings[0])
            recorder.record_output({"dimensions": len(values)})
            recorder.record_usage({"input": result.usage.input_tokens})
            return Embedding(values=values, model=self._model_name)
