import json
from collections.abc import Sequence
from typing import Literal, override

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from opentelemetry.trace import StatusCode
from pydantic_ai.embeddings import Embedder
from pydantic_ai.embeddings.base import EmbeddingModel
from pydantic_ai.embeddings.result import EmbeddingResult
from pydantic_ai.embeddings.settings import EmbeddingSettings
from pydantic_ai.embeddings.test import TestEmbeddingModel

from adapters.out.llm.capture.embedding import OpenRouterEmbeddingAdapter
from adapters.out.llm.tracing import (
    OBSERVATION_INPUT,
    OBSERVATION_MODEL_NAME,
    OBSERVATION_TYPE,
)
from domain.capture.value_objects import Embedding


def _install_in_memory_tracer() -> InMemorySpanExporter:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return exporter


def _adapter(
    model: EmbeddingModel,
    *,
    model_name: str = "openai/text-embedding-3-small",
    dimensions: int | None = None,
) -> OpenRouterEmbeddingAdapter:
    embedder = Embedder(model)
    return OpenRouterEmbeddingAdapter(embedder, model_name, dimensions=dimensions)


class _RaisingEmbeddingModel(EmbeddingModel):
    @property
    @override
    def model_name(self) -> str:
        return "raising"

    @property
    @override
    def system(self) -> str:
        return "test"

    @override
    async def embed(
        self,
        inputs: str | Sequence[str],
        *,
        input_type: Literal["query", "document"] = "query",
        settings: EmbeddingSettings | None = None,
    ) -> EmbeddingResult:
        raise ValueError("provider down")


async def test_embed_maps_provider_vector_into_embedding_with_expected_dimension() -> (
    None
):
    _ = _install_in_memory_tracer()
    adapter = _adapter(TestEmbeddingModel(dimensions=8))

    result = await adapter.embed("TCP handshakes")

    assert isinstance(result, Embedding)
    assert len(result.values) == 8
    assert all(component == 1.0 for component in result.values)


async def test_embed_passes_dimensions_when_reduction_is_configured() -> None:
    model = TestEmbeddingModel(dimensions=8)
    _ = _install_in_memory_tracer()
    adapter = _adapter(model, dimensions=256)

    _ = await adapter.embed("hello")

    last_settings = model.last_settings or {}
    assert last_settings.get("dimensions") == 256


async def test_embed_omits_dimensions_when_reduction_is_unconfigured() -> None:
    model = TestEmbeddingModel(dimensions=8)
    _ = _install_in_memory_tracer()
    adapter = _adapter(model, dimensions=None)

    _ = await adapter.embed("hello")

    last_settings = model.last_settings or {}
    assert "dimensions" not in last_settings


async def test_embed_exports_one_embedding_observation_span_with_input_and_model() -> (
    None
):
    exporter = _install_in_memory_tracer()
    model_name = "openai/text-embedding-3-small"
    text = "TCP handshakes"
    adapter = _adapter(TestEmbeddingModel(dimensions=4), model_name=model_name)

    _ = await adapter.embed(text)

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "embedding"
    attributes = span.attributes
    assert attributes is not None
    assert attributes[OBSERVATION_TYPE] == "embedding"
    observation_input = attributes[OBSERVATION_INPUT]
    assert isinstance(observation_input, str)
    assert json.loads(observation_input) == text
    assert attributes[OBSERVATION_MODEL_NAME] == model_name


async def test_embed_propagates_provider_failure_after_span_records_error() -> None:
    exporter = _install_in_memory_tracer()
    adapter = _adapter(_RaisingEmbeddingModel())

    with pytest.raises(ValueError, match="provider down"):
        _ = await adapter.embed("hello")

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].status.status_code == StatusCode.ERROR
