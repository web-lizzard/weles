from pydantic_ai.embeddings import Embedder

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
        _ = text
        raise NotImplementedError
