"""One-shot embedding smoke test: real provider call and optional Langfuse export."""

from __future__ import annotations

import asyncio
import sys
import time
from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from adapters.out.in_memory.capture.embedding import DeterministicEmbeddingAdapter
from adapters.out.llm.capture.embedding import OpenRouterEmbeddingAdapter
from adapters.telemetry import configure_tracing
from config.settings import EmbeddingProvider, Settings
from domain.capture.ports import EmbeddingPort

if TYPE_CHECKING:
    from pydantic_ai.embeddings import Embedder


def _langfuse_ui_url(settings: Settings) -> str:
    suffix = "/api/public/otel/v1/traces"
    endpoint = settings.langfuse_otlp_endpoint.rstrip("/")
    if endpoint.endswith(suffix):
        return f"{endpoint[: -len(suffix)]}/traces"
    return "https://cloud.langfuse.com/traces"


def _build_embedding_port(settings: Settings) -> EmbeddingPort:
    if settings.embedding_provider == EmbeddingProvider.DETERMINISTIC:
        return DeterministicEmbeddingAdapter()
    from pydantic_ai.embeddings import Embedder
    from pydantic_ai.embeddings.openai import OpenAIEmbeddingModel
    from pydantic_ai.providers.openrouter import OpenRouterProvider

    embedder: Embedder = Embedder(
        OpenAIEmbeddingModel(
            settings.embedding_model,
            provider=OpenRouterProvider(api_key=settings.openrouter_api_key),
        )
    )
    return OpenRouterEmbeddingAdapter(
        embedder,
        settings.embedding_model,
        settings.embedding_dimensions,
    )


def _force_flush_traces() -> None:
    provider = trace.get_tracer_provider()
    if isinstance(provider, TracerProvider):
        _ = provider.force_flush()


async def _run(label: str) -> None:
    settings = Settings()  # pyright: ignore[reportCallIssue]
    configure_tracing(settings)
    embedding = _build_embedding_port(settings)

    started = time.perf_counter()
    result = await embedding.embed(label)
    elapsed = time.perf_counter() - started

    values = result.values
    preview = ", ".join(f"{v:.6f}" for v in values[:5])
    print(f"label: {label}")
    print(f"dimensions: {len(values)}")
    print(f"preview (first 5): [{preview}]")
    print(f"elapsed: {elapsed:.3f}s")

    _force_flush_traces()
    print(_langfuse_ui_url(settings))


def main() -> None:
    label = sys.argv[1] if len(sys.argv) > 1 else "TCP handshakes"
    asyncio.run(_run(label))


if __name__ == "__main__":
    main()
