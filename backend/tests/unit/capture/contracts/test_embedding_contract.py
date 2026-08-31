from collections.abc import Callable
from typing import cast

import pytest

from adapters.out.in_memory.capture.embedding import DeterministicEmbeddingAdapter
from application.capture.ports import EmbeddingPort

_IMPLEMENTATIONS: list[Callable[[], EmbeddingPort]] = [
    cast(Callable[[], EmbeddingPort], DeterministicEmbeddingAdapter),
]


@pytest.mark.parametrize("make_adapter", _IMPLEMENTATIONS, ids=["deterministic"])
async def test_same_text_yields_identical_embedding(
    make_adapter: Callable[[], EmbeddingPort],
) -> None:
    adapter = make_adapter()
    text = "TCP handshakes"

    first = await adapter.embed(text)
    second = await adapter.embed(text)

    assert first == second


@pytest.mark.parametrize("make_adapter", _IMPLEMENTATIONS, ids=["deterministic"])
async def test_embedding_has_stable_nonzero_dimension(
    make_adapter: Callable[[], EmbeddingPort],
) -> None:
    adapter = make_adapter()

    embedding = await adapter.embed("TCP handshakes")

    assert len(embedding.values) > 0


@pytest.mark.parametrize("make_adapter", _IMPLEMENTATIONS, ids=["deterministic"])
async def test_different_texts_yield_different_embeddings(
    make_adapter: Callable[[], EmbeddingPort],
) -> None:
    adapter = make_adapter()

    first = await adapter.embed("TCP handshakes")
    second = await adapter.embed("UDP datagrams")

    assert first != second
