import gc

import pytest


@pytest.fixture(autouse=True)
def _reclaim_dead_core_exception_subclasses(  # pyright: ignore[reportUnusedFunction]
    request: pytest.FixtureRequest,
) -> None:
    # Reference cycles keep test-local CoreException subclasses (from other test
    # modules) alive past their scope; force-collect before the exhaustiveness walk.
    nodeid: str = request.node.nodeid  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
    if "test_http_error_mapping" in nodeid:
        _ = gc.collect()
