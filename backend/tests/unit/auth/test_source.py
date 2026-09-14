"""Who a request is attributed to, for attempt limiting."""

from adapters.auth.source import resolve_attempt_source


def test_the_peer_is_the_source_when_it_is_not_a_trusted_proxy() -> None:
    source = resolve_attempt_source(
        peer="203.0.113.9",
        forwarded_for="198.51.100.7",
        trusted_proxies=frozenset({"203.0.113.1"}),
    )

    assert source.value == "203.0.113.9"


def test_the_rightmost_untrusted_forwarded_entry_wins_behind_a_trusted_peer() -> None:
    source = resolve_attempt_source(
        peer="203.0.113.1",
        forwarded_for="198.51.100.7, 192.0.2.5, 203.0.113.2",
        trusted_proxies=frozenset({"203.0.113.1", "203.0.113.2"}),
    )

    assert source.value == "192.0.2.5"


def test_the_peer_is_the_source_when_every_forwarded_entry_is_trusted() -> None:
    source = resolve_attempt_source(
        peer="203.0.113.1",
        forwarded_for="203.0.113.2, 203.0.113.1",
        trusted_proxies=frozenset({"203.0.113.1", "203.0.113.2"}),
    )

    assert source.value == "203.0.113.1"


def test_the_source_is_unknown_when_there_is_no_peer_and_no_trusted_header() -> None:
    source = resolve_attempt_source(
        peer=None,
        forwarded_for="198.51.100.7",
        trusted_proxies=frozenset(),
    )

    assert source.value == "unknown"
