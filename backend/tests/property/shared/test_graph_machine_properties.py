# pyright: reportUnusedParameter=false
"""Property tests over StateMachine mechanics (llm-adapter-capture-modes phase 3)."""

from collections.abc import Mapping
from enum import StrEnum
from typing import override

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from unit.shared.graph_instruction_builder import GRAPH_TEST_INSTRUCTION_BUILDER

from domain.shared.graph.machine import StateMachine
from domain.shared.graph.model import (
    Action,
    EdgeCondition,
    Graph,
    State,
    Tool,
    ToolResult,
    Transition,
)
from domain.shared.instruction.model import InstructionBuilder


class _Node(StrEnum):
    A = "a"
    B = "b"
    C = "c"


_ALL_NODES = list(_Node)


class _Context:
    phase: _Node
    flag: bool

    def __init__(self, phase: _Node, *, flag: bool = False) -> None:
        self.phase = phase
        self.flag = flag


def _flag_guard(context: _Context) -> bool:
    return context.flag


class _Described(State[_Context, object, str]):
    def __init__(self, label: str) -> None:
        self._label: str = label

    @property
    @override
    def tools(self) -> tuple[Tool[_Context, ToolResult], ...]:
        return ()

    @property
    @override
    def actions(self) -> tuple[Action[_Context, object, str], ...]:
        return ()

    @property
    @override
    def instruction_builder(self) -> InstructionBuilder[_Context]:
        return GRAPH_TEST_INSTRUCTION_BUILDER

    @property
    @override
    def description(self) -> str:
        return self._label


class _ProbeMachine(StateMachine[_Context, object, str, _Node]):
    def __init__(
        self, context: _Context, graph: Graph[_Context, object, str, _Node]
    ) -> None:
        super().__init__(context, object())
        self._graph: Graph[_Context, object, str, _Node] = graph

    @property
    @override
    def graph(self) -> Graph[_Context, object, str, _Node]:
        return self._graph

    @override
    def state_name_of(self, context: _Context) -> _Node:
        return context.phase

    @override
    def enter_state(self, context: _Context, name: _Node) -> None:
        context.phase = name


def _reference_available(
    graph: Graph[_Context, object, str, _Node], context: _Context, source: _Node
) -> dict[_Node, str]:
    available: dict[_Node, str] = {}
    for target, edge in graph.outgoing(source).items():
        guard = edge.guard
        if guard is not None and not guard(context):
            continue
        available[target] = graph.states[target].description
    return available


def _graph_from_edge_specs(
    specs: Mapping[tuple[_Node, _Node], tuple[bool, str]],
) -> Graph[_Context, object, str, _Node]:
    states = {node: _Described(f"State {node.value}.") for node in _ALL_NODES}
    transitions: dict[_Node, dict[_Node, Transition[_Context, object, str]]] = {}
    for (source, target), (needs_flag, _label) in specs.items():
        guard: EdgeCondition[_Context] | None
        guard = _flag_guard if needs_flag else None
        edge = Transition[_Context, object, str](guard=guard)
        transitions.setdefault(source, {})[target] = edge
    return Graph[_Context, object, str, _Node](states=states, transitions=transitions)


_edge_key_strategy = st.tuples(
    st.sampled_from(_ALL_NODES),
    st.sampled_from(_ALL_NODES),
).filter(lambda pair: pair[0] != pair[1])

_edge_specs_strategy = st.dictionaries(
    _edge_key_strategy,
    st.tuples(st.booleans(), st.text(min_size=1, max_size=12)),
    max_size=6,
)


@given(
    specs=_edge_specs_strategy,
    start=st.sampled_from(_ALL_NODES),
    flag=st.booleans(),
)
@settings(max_examples=100, deadline=None)
def test_available_transitions_matches_guard_filtered_outgoing_descriptions(
    specs: Mapping[tuple[_Node, _Node], tuple[bool, str]],
    start: _Node,
    flag: bool,
) -> None:
    graph = _graph_from_edge_specs(specs)
    context = _Context(start, flag=flag)
    machine = _ProbeMachine(context, graph)

    expected = _reference_available(graph, context, start)
    assert dict(machine.available_transitions()) == expected


@given(
    specs=_edge_specs_strategy,
    start=st.sampled_from(_ALL_NODES),
    flag=st.booleans(),
    target=st.sampled_from(_ALL_NODES),
)
@settings(max_examples=100, deadline=None)
@pytest.mark.asyncio
async def test_transition_succeeds_only_when_target_is_currently_available(
    specs: Mapping[tuple[_Node, _Node], tuple[bool, str]],
    start: _Node,
    flag: bool,
    target: _Node,
) -> None:
    graph = _graph_from_edge_specs(specs)
    context = _Context(start, flag=flag)
    machine = _ProbeMachine(context, graph)
    before = context.phase
    available = _reference_available(graph, context, start)

    moved = await machine.transition(target)

    if target in available:
        assert moved is True
        assert context.phase is target
    else:
        assert moved is False
        assert context.phase is before


@given(
    specs=_edge_specs_strategy,
    start=st.sampled_from(_ALL_NODES),
    flag=st.booleans(),
)
@settings(max_examples=100, deadline=None)
def test_get_tools_equals_current_state_get_tools_for_same_context(
    specs: Mapping[tuple[_Node, _Node], tuple[bool, str]],
    start: _Node,
    flag: bool,
) -> None:
    graph = _graph_from_edge_specs(specs)
    context = _Context(start, flag=flag)
    machine = _ProbeMachine(context, graph)

    assert machine.get_tools() == machine.current_state.get_tools(context)
