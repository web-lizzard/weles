from datetime import UTC, datetime, timedelta

from adapters.out.in_memory.remember.clock import SystemClock


def test_now_returns_a_timezone_aware_instant_in_utc_between_two_wall_clock_reads() -> (
    None
):
    before = datetime.now(UTC)
    now = SystemClock().now()
    after = datetime.now(UTC)

    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)
    assert before <= now <= after
