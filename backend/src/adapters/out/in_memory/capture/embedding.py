import hashlib

from domain.capture.value_objects import Embedding

_EMBEDDING_DIMENSION = 32


class DeterministicEmbeddingAdapter:
    async def embed(self, text: str) -> Embedding:
        digest = hashlib.sha512(text.strip().encode()).digest()
        values = tuple((byte - 127.5) / 127.5 for byte in digest[:_EMBEDDING_DIMENSION])
        return Embedding(values=values)
