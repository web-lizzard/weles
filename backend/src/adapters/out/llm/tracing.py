# pyright: reportUnusedParameter=false

from collections.abc import Generator, Mapping
from contextlib import contextmanager

OBSERVATION_TYPE = "langfuse.observation.type"
OBSERVATION_INPUT = "langfuse.observation.input"
OBSERVATION_OUTPUT = "langfuse.observation.output"
OBSERVATION_MODEL_NAME = "langfuse.observation.model.name"
OBSERVATION_USAGE_DETAILS = "langfuse.observation.usage_details"


class ObservationRecorder:
    def record_output(self, output: object) -> None:
        raise NotImplementedError

    def record_model(self, model_name: str) -> None:
        raise NotImplementedError

    def record_usage(self, usage: Mapping[str, int]) -> None:
        raise NotImplementedError


@contextmanager
def observation(
    name: str, *, observation_type: str, input_value: object
) -> Generator[ObservationRecorder, None, None]:
    _ = (name, observation_type, input_value)
    raise NotImplementedError
