import json
from collections.abc import Generator, Mapping
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

OBSERVATION_TYPE = "langfuse.observation.type"
OBSERVATION_INPUT = "langfuse.observation.input"
OBSERVATION_OUTPUT = "langfuse.observation.output"
OBSERVATION_MODEL_NAME = "langfuse.observation.model.name"
OBSERVATION_USAGE_DETAILS = "langfuse.observation.usage_details"


class ObservationRecorder:
    _span: trace.Span

    def __init__(self, span: trace.Span) -> None:
        self._span = span

    def record_output(self, output: object) -> None:
        self._span.set_attribute(OBSERVATION_OUTPUT, json.dumps(output))

    def record_model(self, model_name: str) -> None:
        self._span.set_attribute(OBSERVATION_MODEL_NAME, model_name)

    def record_usage(self, usage: Mapping[str, int]) -> None:
        self._span.set_attribute(OBSERVATION_USAGE_DETAILS, json.dumps(dict(usage)))


@contextmanager
def observation(
    name: str, *, observation_type: str, input_value: object
) -> Generator[ObservationRecorder, None, None]:
    with trace.get_tracer(__name__).start_as_current_span(name) as span:
        span.set_attribute(OBSERVATION_TYPE, observation_type)
        span.set_attribute(OBSERVATION_INPUT, json.dumps(input_value))
        recorder = ObservationRecorder(span)
        try:
            yield recorder
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            raise
