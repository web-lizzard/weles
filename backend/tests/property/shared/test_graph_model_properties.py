# pyright: reportUnusedParameter=false
"""Property tests over shared graph mechanics (llm-adapter-capture-modes phase 1)."""

from collections.abc import Mapping
from enum import StrEnum
from typing import override

from hypothesis import given, settings
from hypothesis import strategies as st

from domain.shared.graph.model import (
    Action,
    Graph,
    State,
    Tool,
    ToolResult,
    Transition,
)


class _Node(StrEnum):
    A = "a"
    B = "b"
    C = "c"
    D = "d"


_ALL_NODES = list(_Node)


class _Bare(State[object, object, str]):
    @property
    @override
    def tools(self) -> tuple[Tool[object, ToolResult], ...]:
        return ()

    @property
    @override
    def actions(self) -> tuple[Action[object, object, str], ...]:
        return ()

    @property
    @override
    def description(self) -> str:
        return "Bare state for topology property tests."


def _reference_reachable(
    transitions: Mapping[_Node, Mapping[_Node, object]], source: _Node
) -> frozenset[_Node]:
    reached: set[_Node] = set()
    frontier = list(transitions.get(source, {}))
    while frontier:
        name = frontier.pop()
        if name in reached:
            continue
        reached.add(name)
        for target in transitions.get(name, {}):
            if target not in reached:
                frontier.append(target)
    return frozenset(reached)


def _graph_from_adjacency(
    adjacency: Mapping[_Node, frozenset[_Node]],
) -> Graph[object, object, str, _Node]:
    states = {node: _Bare() for node in _ALL_NODES}
    transitions: dict[_Node, dict[_Node, Transition[object, object, str]]] = {}
    for source, targets in adjacency.items():
        if not targets:
            continue
        transitions[source] = {
            target: Transition[object, object, str]() for target in targets
        }
    return Graph[object, object, str, _Node](states=states, transitions=transitions)


_adjacency_strategy = st.fixed_dictionaries(
    {
        node: st.frozensets(st.sampled_from(_ALL_NODES), max_size=4)
        for node in _ALL_NODES
    }
).map(
    lambda adj: {
        source: frozenset(t for t in targets if t != source)
        for source, targets in adj.items()
    }
)


@given(adjacency=_adjacency_strategy)
@settings(max_examples=100, deadline=None)
def test_reachable_from_matches_independent_bfs_on_the_adjacency(
    adjacency: Mapping[_Node, frozenset[_Node]],
) -> None:
    graph = _graph_from_adjacency(adjacency)

    for source in _ALL_NODES:
        expected = _reference_reachable(graph.transitions, source)
        assert graph.reachable_from(source) == expected


@given(adjacency=_adjacency_strategy)
@settings(max_examples=100, deadline=None)
def test_terminal_states_are_exactly_states_with_no_outgoing_edge_in_the_declaration(
    adjacency: Mapping[_Node, frozenset[_Node]],
) -> None:
    graph = _graph_from_adjacency(adjacency)

    expected = frozenset(
        node for node in _ALL_NODES if not graph.transitions.get(node, {})
    )
    assert graph.terminal_states == expected
    for node in _ALL_NODES:
        assert graph.is_terminal(node) == (node in expected)


@given(adjacency=_adjacency_strategy)
@settings(max_examples=100, deadline=None)
def test_every_reachable_state_is_a_declared_state_key(
    adjacency: Mapping[_Node, frozenset[_Node]],
) -> None:
    graph = _graph_from_adjacency(adjacency)
    declared = frozenset(graph.states)

    for source in _ALL_NODES:
        reached = graph.reachable_from(source)
        assert reached <= declared
