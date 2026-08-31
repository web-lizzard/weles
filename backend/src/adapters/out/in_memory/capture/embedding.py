from domain.capture.value_objects import Embedding


class DeterministicEmbeddingAdapter:
    async def embed(self, _text: str) -> Embedding:
        raise NotImplementedError
