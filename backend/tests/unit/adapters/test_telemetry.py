from adapters.telemetry import langfuse_otlp_traces_endpoint


def test_langfuse_otlp_traces_endpoint_appends_v1_traces_suffix() -> None:
    assert (
        langfuse_otlp_traces_endpoint("https://cloud.langfuse.com/api/public/otel")
        == "https://cloud.langfuse.com/api/public/otel/v1/traces"
    )


def test_langfuse_otlp_traces_endpoint_leaves_full_url_unchanged() -> None:
    url = "https://cloud.langfuse.com/api/public/otel/v1/traces"
    assert langfuse_otlp_traces_endpoint(url) == url
