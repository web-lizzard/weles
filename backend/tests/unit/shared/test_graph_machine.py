from enum import StrEnum
from typing import Literal, cast, override

from domain.shared.graph.machine import StateMachine
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


class _Deps:
    token: str

    def __init__(self, token: str) -> None:
        self.token = token


class _Context:
    phase: _Phase

    def __init__(self, phase: _Phase) -> None:
        self.phase = phase


class _PingResult(ToolResult, frozen=True):
    tool: Literal["ping"] = "ping"


async def _ping(_context: _Context, _arguments: ToolArguments) -> _PingResult:
    return _PingResult()


_PING = Tool[_Context, _PingResult](
    name="ping",
    description="Signal that the open phase is still live.",
    result=_PingResult,
    handler=_ping,
)


class _Open(State[_Context, _Deps, str]):
    @property
    @override
    def tools(self) -> tuple[Tool[_Context, ToolResult], ...]:
        return (_PING,)

    @property
    @override
    def actions(self) -> tuple[Action[_Context, _Deps, str], ...]:
        return ()

    @property
    @override
    def instruction_builder(self) -> InstructionBuilder[_Context]:
        return GRAPH_TEST_INSTRUCTION_BUILDER

    @property
    @override
    def description(self) -> str:
        return "Open intake phase."


class _Waiting(State[_Context, _Deps, str]):
    @property
    @override
    def tools(self) -> tuple[Tool[_Context, ToolResult], ...]:
        return ()

    @property
    @override
    def actions(self) -> tuple[Action[_Context, _Deps, str], ...]:
        return ()

    @property
    @override
    def instruction_builder(self) -> InstructionBuilder[_Context]:
        return GRAPH_TEST_INSTRUCTION_BUILDER

    @property
    @override
    def description(self) -> str:
        return "Waiting before closure."


class _Closed(State[_Context, _Deps, str]):
    @property
    @override
    def tools(self) -> tuple[Tool[_Context, ToolResult], ...]:
        return ()

    @property
    @override
    def actions(self) -> tuple[Action[_Context, _Deps, str], ...]:
        return ()

    @property
    @override
    def instruction_builder(self) -> InstructionBuilder[_Context]:
        return GRAPH_TEST_INSTRUCTION_BUILDER

    @property
    @override
    def description(self) -> str:
        return "Closed intake phase."


def _intake_graph(
    *,
    waiting_guard: EdgeCondition[_Context] | None = None,
    open_actions: tuple[EdgeAction[_Context, _Deps], ...] = (),
    waiting_actions: tuple[EdgeAction[_Context, _Deps], ...] = (),
) -> Graph[_Context, _Deps, str, _Phase]:
    return Graph[_Context, _Deps, str, _Phase](
        states={
            _Phase.OPEN: _Open(),
            _Phase.WAITING: _Waiting(),
            _Phase.CLOSED: _Closed(),
        },
        transitions={
            _Phase.OPEN: {
                _Phase.WAITING: Transition[_Context, _Deps, str](actions=open_actions),
            },
            _Phase.WAITING: {
                _Phase.CLOSED: Transition[_Context, _Deps, str](
                    guard=waiting_guard,
                    actions=waiting_actions,
                ),
            },
        },
    )


class _IntakeMachine(StateMachine[_Context, _Deps, str, _Phase]):
    _graph: Graph[_Context, _Deps, str, _Phase]

    def __init__(
        self,
        context: _Context,
        deps: _Deps,
        graph: Graph[_Context, _Deps, str, _Phase],
    ) -> None:
        super().__init__(context, deps)
        self._graph = graph

    @property
    @override
    def graph(self) -> Graph[_Context, _Deps, str, _Phase]:
        return self._graph

    @override
    def state_name_of(self, context: _Context) -> _Phase:
        return context.phase

    @override
    def enter_state(self, context: _Context, name: _Phase) -> None:
        context.phase = name


def _machine(
    phase: _Phase = _Phase.OPEN,
    *,
    deps: _Deps | None = None,
    waiting_guard: EdgeCondition[_Context] | None = None,
    open_actions: tuple[EdgeAction[_Context, _Deps], ...] = (),
    waiting_actions: tuple[EdgeAction[_Context, _Deps], ...] = (),
) -> _IntakeMachine:
    context = _Context(phase)
    resolved_deps = deps if deps is not None else _Deps("machine-default")
    graph = _intake_graph(
        waiting_guard=waiting_guard,
        open_actions=open_actions,
        waiting_actions=waiting_actions,
    )
    return _IntakeMachine(context, resolved_deps, graph)


def test_current_state_and_name_resolve_from_the_aggregate_phase_field() -> None:
    machine = _machine(_Phase.WAITING)

    assert machine.current_state_name is _Phase.WAITING
    assert machine.current_state is machine.graph.states[_Phase.WAITING]
    assert machine.context.phase is _Phase.WAITING


def test_get_tools_delegates_to_the_current_state_for_this_context() -> None:
    machine = _machine(_Phase.OPEN)

    assert machine.get_tools() == (_PING,)


async def test_apply_runs_matching_state_actions_without_leaving_the_phase() -> None:
    invoked: list[str] = []

    async def stamp(_context: _Context, _deps: _Deps, _event: str) -> None:
        invoked.append("state-action")

    class _Stamping(State[_Context, _Deps, str]):
        @property
        @override
        def tools(self) -> tuple[Tool[_Context, ToolResult], ...]:
            return ()

        @property
        @override
        def actions(self) -> tuple[Action[_Context, _Deps, str], ...]:
            return (stamp,)

        @property
        @override
        def instruction_builder(self) -> InstructionBuilder[_Context]:
            return GRAPH_TEST_INSTRUCTION_BUILDER

        @property
        @override
        def description(self) -> str:
            return "Stamping on events."

        @override
        def get_actions(
            self, context: _Context, event: str
        ) -> tuple[Action[_Context, _Deps, str], ...]:
            _ = context
            return (stamp,) if event == "arrived" else ()

    graph = Graph[_Context, _Deps, str, _Phase](
        states={
            _Phase.OPEN: _Stamping(),
            _Phase.WAITING: _Waiting(),
            _Phase.CLOSED: _Closed(),
        },
        transitions={
            _Phase.OPEN: {_Phase.WAITING: Transition[_Context, _Deps, str]()},
        },
    )
    context = _Context(_Phase.OPEN)
    machine = _IntakeMachine(context, _Deps("apply-stamp"), graph)

    await machine.apply("arrived")

    assert invoked == ["state-action"]
    assert machine.current_state_name is _Phase.OPEN


def test_available_transitions_lists_only_guarded_targets_mapped_to_descriptions() -> (
    None
):
    guard_invoked: list[str] = []

    def refuse(_context: _Context) -> bool:
        guard_invoked.append("waiting-guard")
        return False

    def allow(_context: _Context) -> bool:
        guard_invoked.append("close-guard")
        return True

    graph = Graph[_Context, _Deps, str, _Phase](
        states={
            _Phase.OPEN: _Open(),
            _Phase.WAITING: _Waiting(),
            _Phase.CLOSED: _Closed(),
        },
        transitions={
            _Phase.OPEN: {
                _Phase.WAITING: Transition[_Context, _Deps, str](),
                _Phase.CLOSED: Transition[_Context, _Deps, str](guard=allow),
            },
            _Phase.WAITING: {
                _Phase.CLOSED: Transition[_Context, _Deps, str](guard=refuse),
            },
        },
    )
    machine = _IntakeMachine(_Context(_Phase.OPEN), _Deps("available"), graph)

    assert machine.available_transitions() == {
        _Phase.WAITING: "Waiting before closure.",
        _Phase.CLOSED: "Closed intake phase.",
    }
    assert guard_invoked == ["close-guard"]

    waiting_machine = _IntakeMachine(
        _Context(_Phase.WAITING), _Deps("available-waiting"), graph
    )
    assert waiting_machine.available_transitions() == {}
    assert guard_invoked == ["close-guard", "waiting-guard"]


async def test_transition_runs_edge_actions_and_writes_the_new_phase_when_allowed() -> (
    None
):
    edge_invoked: list[str] = []

    async def seal(_context: _Context, _deps: _Deps) -> None:
        edge_invoked.append("seal")

    machine = _machine(open_actions=(seal,))

    moved = await machine.transition(_Phase.WAITING)

    assert moved is True
    assert edge_invoked == ["seal"]
    assert machine.current_state_name is _Phase.WAITING
    assert machine.context.phase is _Phase.WAITING


async def test_transition_refuses_a_target_that_is_not_currently_available() -> None:
    edge_invoked: list[str] = []

    async def seal(_context: _Context, _deps: _Deps) -> None:
        edge_invoked.append("seal")

    def refuse(_context: _Context) -> bool:
        return False

    machine = _machine(
        _Phase.WAITING,
        waiting_guard=refuse,
        waiting_actions=(seal,),
    )

    moved = await machine.transition(_Phase.CLOSED)

    assert moved is False
    assert edge_invoked == []
    assert machine.current_state_name is _Phase.WAITING


async def test_apply_passes_construction_deps_to_state_actions() -> None:
    deps = _Deps("apply-forward")
    received: list[_Deps] = []

    async def record_deps(_context: _Context, passed_deps: _Deps, _event: str) -> None:
        received.append(passed_deps)

    class _Recording(State[_Context, _Deps, str]):
        @property
        @override
        def tools(self) -> tuple[Tool[_Context, ToolResult], ...]:
            return ()

        @property
        @override
        def actions(self) -> tuple[Action[_Context, _Deps, str], ...]:
            return (cast(Action[_Context, _Deps, str], record_deps),)

        @property
        @override
        def instruction_builder(self) -> InstructionBuilder[_Context]:
            return GRAPH_TEST_INSTRUCTION_BUILDER

        @property
        @override
        def description(self) -> str:
            return "Records deps on events."

        @override
        def get_actions(
            self, context: _Context, event: str
        ) -> tuple[Action[_Context, _Deps, str], ...]:
            _ = context
            stamped = cast(Action[_Context, _Deps, str], record_deps)
            return (stamped,) if event == "arrived" else ()

    graph = Graph[_Context, _Deps, str, _Phase](
        states={
            _Phase.OPEN: _Recording(),
            _Phase.WAITING: _Waiting(),
            _Phase.CLOSED: _Closed(),
        },
        transitions={
            _Phase.OPEN: {_Phase.WAITING: Transition[_Context, _Deps, str]()},
        },
    )
    machine = _IntakeMachine(_Context(_Phase.OPEN), deps, graph)

    await machine.apply("arrived")

    assert received == [deps]
    assert received[0] is deps


async def test_transition_passes_construction_deps_to_edge_actions() -> None:
    deps = _Deps("transition-forward")
    received: list[_Deps] = []

    async def record_deps(_context: _Context, passed_deps: _Deps) -> None:
        received.append(passed_deps)

    machine = _machine(
        _Phase.OPEN,
        deps=deps,
        open_actions=(cast(EdgeAction[_Context, _Deps], record_deps),),
    )

    moved = await machine.transition(_Phase.WAITING)

    assert moved is True
    assert received == [deps]
    assert received[0] is deps
