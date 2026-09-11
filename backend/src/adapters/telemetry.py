from base64 import b64encode

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from config.settings import Settings


def configure_tracing(settings: Settings) -> None:
    if not settings.tracing_enabled:
        return
    public_key = settings.langfuse_public_key
    secret_key = settings.langfuse_secret_key
    if not public_key or not secret_key:
        return

    credentials = f"{public_key}:{secret_key}"
    headers = {
        "Authorization": f"Basic {b64encode(credentials.encode()).decode()}",
        "x-langfuse-ingestion-version": "4",
    }
    exporter = OTLPSpanExporter(
        endpoint=settings.langfuse_otlp_endpoint,
        headers=headers,
    )
    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
