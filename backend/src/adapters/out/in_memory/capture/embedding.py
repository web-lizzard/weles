import hashlib
import struct

from domain.capture.value_objects import Embedding

_EMBEDDING_DIMENSION = 32


class DeterministicEmbeddingAdapter:
    async def embed(self, text: str) -> Embedding:
        digest = hashlib.sha512(text.strip().encode()).digest()
        values = struct.unpack(f">{_EMBEDDING_DIMENSION}d", digest)
        return Embedding(values=values)
