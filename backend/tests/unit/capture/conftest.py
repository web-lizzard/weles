# pyright: reportPrivateUsage=false, reportUnusedFunction=false

import pytest
from opentelemetry import trace


@pytest.fixture(autouse=True)
def _reset_tracer_provider() -> None:
    trace._TRACER_PROVIDER_SET_ONCE._done = False
    trace._TRACER_PROVIDER = None
