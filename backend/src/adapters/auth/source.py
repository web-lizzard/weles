from adapters.auth.model import AttemptSource


def resolve_attempt_source(
    peer: str | None,
    forwarded_for: str | None,
    trusted_proxies: frozenset[str],
) -> AttemptSource:
    """Who a request comes from, for attempt limiting.

    `forwarded_for` is consulted only when `peer` is itself listed in
    `trusted_proxies`; an untrusted peer's header is ignored entirely and the
    peer is the source. When it is consulted, entries are comma-split and
    stripped, and walked from the right — the first entry that is not itself
    a trusted proxy wins. When the header is absent, every entry is trusted,
    or there is no peer at all, the source is the peer, or `"unknown"` when
    there is none.
    """
    if peer is not None and peer in trusted_proxies and forwarded_for:
        entries = [entry.strip() for entry in forwarded_for.split(",")]
        for entry in reversed(entries):
            if entry not in trusted_proxies:
                return AttemptSource(value=entry)
    return AttemptSource(value=peer or "unknown")
