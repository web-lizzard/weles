from adapters.auth.model import AttemptSource


def resolve_attempt_source(
    peer: str | None,
    forwarded_for: str | None,
    trusted_proxies: frozenset[str],
) -> AttemptSource:
    """Who a request comes from, for attempt limiting.

    This phase ignores `forwarded_for` and `trusted_proxies` and returns the
    peer, or `"unknown"` when there is none. Phase 6 walks `forwarded_for`
    from the right, past trusted proxies, when `peer` is itself trusted.
    """
    del forwarded_for, trusted_proxies
    return AttemptSource(value=peer or "unknown")
