from enum import StrEnum
from typing import Literal, override

import pytest

from domain.shared.graph.model import (
    Action,
    EdgeAction,
    EdgeCondition,
    Graph,
    State,
    Tool,
    ToolArguments,
    ToolResult,
    Transition,
)
from domain.shared.instruction.model import InstructionBuilder

from .graph_instruction_builder import GRAPH_TEST_INSTRUCTION_BUILDER


class _Phase(StrEnum):
    OPEN = "open"
    WAITING = "waiting"
    CLOSED = "closed"


class _PingResult(ToolResult, frozen=True):
    tool: Literal["ping"] = "ping"


class _PongResult(ToolResult, frozen=True):
    tool: Literal["pong"] = "pong"


async def _ping(_context: object, _arguments: ToolArguments) -> _PingResult:
    return _PingResult()


async def _pong(_context: object, _arguments: ToolArguments) -> _PongResult:
    return _PongResult()


async def _noop(_context: object, _deps: object, _event: str) -> None:
    return None


def _never(_context: object) -> bool:
    return False


_PING = Tool[object, _PingResult](
    name="ping",
    description="Signal that the open phase is still live.",
    result=_PingResult,
    handler=_ping,
)


class _Open(State[object, object, str]):
    @property
    @override
    def tools(self) -> tuple[Tool[object, ToolResult], ...]:
        return (_PING,)

    @property
    @override
    def actions(self) -> tuple[Action[object, object, str], ...]:
        return (_noop,)

    @property
    @override
    def instruction_builder(self) -> InstructionBuilder[object]:
        return GRAPH_TEST_INSTRUCTION_BUILDER

    @property
    @override
    def description(self) -> str:
        return "Open intake phase."


class _Waiting(State[object, object, str]):
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
    def instruction_builder(self) -> InstructionBuilder[object]:
        return GRAPH_TEST_INSTRUCTION_BUILDER

    @property
    @override
    def description(self) -> str:
        return "Waiting before closure."


class _Closed(State[object, object, str]):
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
    def instruction_builder(self) -> InstructionBuilder[object]:
        return GRAPH_TEST_INSTRUCTION_BUILDER

    @property
    @override
    def description(self) -> str:
        return "Closed intake phase."


def _intake_graph(
    *,
    waiting_guard: EdgeCondition[object] | None = _never,
    open_actions: tuple[EdgeAction[object, object], ...] = (),
    waiting_actions: tuple[EdgeAction[object, object], ...] = (),
) -> Graph[object, object, str, _Phase]:
    return Graph[object, object, str, _Phase](
        states={
            _Phase.OPEN: _Open(),
            _Phase.WAITING: _Waiting(),
            _Phase.CLOSED: _Closed(),
        },
        transitions={
            _Phase.OPEN: {
                _Phase.WAITING: Transition[object, object, str](
                    edge_actions=open_actions
                ),
            },
            _Phase.WAITING: {
                _Phase.CLOSED: Transition[object, object, str](
                    guard=waiting_guard,
                    edge_actions=waiting_actions,
                ),
            },
        },
    )


def test_get_tools_offers_the_whole_inventory_when_the_state_does_not_filter() -> None:
    state = _Open()

    assert state.get_tools(object()) == state.tools


def test_get_actions_offers_the_whole_inventory_when_the_state_does_not_filter() -> (
    None
):
    invoked: list[str] = []

    async def stamp(_context: object, _deps: object, _event: str) -> None:
        invoked.append("state-action")

    class _Stamping(State[object, object, str]):
        @property
        @override
        def tools(self) -> tuple[Tool[object, ToolResult], ...]:
            return ()

        @property
        @override
        def actions(self) -> tuple[Action[object, object, str], ...]:
            return (stamp,)

        @property
        @override
        def instruction_builder(self) -> InstructionBuilder[object]:
            return GRAPH_TEST_INSTRUCTION_BUILDER

        @property
        @override
        def description(self) -> str:
            return "Stamping state-action on events."

    state = _Stamping()

    assert state.get_actions(object(), "arrived") == (stamp,)
    assert invoked == []


def test_outgoing_lists_edges_by_target_and_is_empty_when_the_source_has_none() -> None:
    invoked: list[str] = []

    def refuse(_context: object) -> bool:
        invoked.append("guard")
        return False

    async def seal(_context: object, _deps: object) -> None:
        invoked.append("edge-action")

    graph = _intake_graph(waiting_guard=refuse, open_actions=(seal,))

    assert graph.outgoing(_Phase.OPEN) == {
        _Phase.WAITING: Transition[object, object, str](edge_actions=(seal,)),
    }
    assert graph.outgoing(_Phase.WAITING) == {
        _Phase.CLOSED: Transition[object, object, str](guard=refuse),
    }
    assert graph.outgoing(_Phase.CLOSED) == {}
    assert invoked == []


def test_terminal_states_are_those_with_no_outgoing_edge() -> None:
    graph = _intake_graph()

    assert graph.is_terminal(_Phase.CLOSED) is True
    assert graph.is_terminal(_Phase.OPEN) is False
    assert graph.terminal_states == frozenset({_Phase.CLOSED})


def test_reachable_from_follows_edges_without_evaluating_guards() -> None:
    invoked: list[str] = []

    def refuse(_context: object) -> bool:
        invoked.append("guard")
        return False

    async def seal(_context: object, _deps: object) -> None:
        invoked.append("edge-action")

    graph = _intake_graph(
        waiting_guard=refuse,
        open_actions=(seal,),
        waiting_actions=(seal,),
    )

    assert graph.reachable_from(_Phase.OPEN) == frozenset(
        {_Phase.WAITING, _Phase.CLOSED}
    )
    assert graph.reachable_from(_Phase.WAITING) == frozenset({_Phase.CLOSED})
    assert graph.reachable_from(_Phase.CLOSED) == frozenset()
    assert invoked == []


def test_a_misnamed_tool_result_discriminator_makes_the_tool_unconstructible() -> None:
    with pytest.raises(ValueError):
        _ = Tool[object, _PongResult](
            name="ping",
            description="Mislabeled on purpose.",
            result=_PongResult,
            handler=_pong,
        )
