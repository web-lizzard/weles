from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import override

from domain.shared.graph.model import Graph, State, StructuredState, Tool, ToolResult
from domain.shared.instruction.model import Instruction


class StateMachine[ContextT, DepsT, EventT, NameT: StrEnum](ABC):
    """The mechanics of a phase graph, generic over the aggregate it carries,
    the event type a turn feeds it, and the enum naming its states.

    Knows nothing of any particular flow: a concrete machine declares one
    `Graph` and says where on the aggregate the current state name lives. Those
    are the only two things a composition supplies — everything else here is
    mechanics. The machine holds no model-facing port and never consumes a
    stream — the application owns the iterator and decides when a transition is
    evaluated. It never persists and never commits.
    """

    def __init__(self, context: ContextT, deps: DepsT) -> None:
        self._context: ContextT = context
        self._deps: DepsT = deps

    @property
    def context(self) -> ContextT:
        """The aggregate the machine carries. The caller reads what a turn
        touched from here — no separate record of changes is returned."""
        return self._context

    @property
    def deps(self) -> DepsT:
        """Collaborators forwarded to state and edge actions for this turn."""
        return self._deps

    @property
    def current_state(self) -> State[ContextT, DepsT, EventT]:
        """The declared state the context's state name resolves to."""
        return self.graph.states[self.current_state_name]

    @property
    def current_state_name(self) -> NameT:
        """The state name currently held on the aggregate."""
        return self.state_name_of(self._context)

    def get_tools(self) -> Sequence[Tool[ContextT, ToolResult]]:
        """What the current state offers the context this turn — the machine
        asks the state and hands the answer on unchanged.

        What this does not return is never rendered to the model and so can
        never be called.
        """
        return self.current_state.get_tools(self._context)

    def build_instruction(self) -> Instruction:
        """What the current state would tell a model this turn — the machine
        asks the state and hands the answer on unchanged.

        Unimplemented on the base class until a concrete machine wires the hook.
        """
        raise NotImplementedError

    async def apply(self, event: EventT) -> None:
        """Feed one event of a turn to the machine.

        Runs the actions the current state says this event warrants. Crosses no
        edge — a move is a separate, explicitly requested act.
        """
        for action in self.current_state.get_actions(self._context, event):
            await action(self._context, self._deps, event)

    def available_transitions(self) -> Mapping[NameT, str]:
        """Every target reachable from the current state whose guard passes,
        mapped to that state's description."""
        context = self._context
        source = self.current_state_name
        available: dict[NameT, str] = {}
        for target, edge in self.graph.outgoing(source).items():
            guard = edge.guard
            if guard is not None and not guard(context):
                continue
            available[target] = self.graph.states[target].description
        return available

    async def advance(self) -> bool:
        """Take the one move the guards select, through `transition`. Returns
        whether a move happened.

        For a flow whose moves are decided by guards rather than chosen by a
        caller. Built on `available_transitions`, which stays the answer to
        "what is permitted now"; this answers "where does the flow go" and
        goes there in the same act. No separate query for the selected target:
        its only reader would be this method, and a test pins a route by
        advancing a context and reading the phase off it.

        Refuses — returns `False` — when no guard passes, when the state is
        terminal, and when more than one guard passes. The last is a mistake
        in the declaration, not a runtime condition: a composition that routes
        by guards pins their mutual exclusivity in its own suite, and the
        machine refuses rather than guesses, the same refusal-as-answer as
        `transition`.

        One edge, like every move. A caller loops over `advance` to walk a
        flow, and each phase entered gets its own step before the next
        `advance` — so a phase is never crossed without its work.
        """
        if self.graph.is_terminal(self.current_state_name):
            return False
        available = self.available_transitions()
        if len(available) != 1:
            return False
        target = next(iter(available))
        return await self.transition(target)

    async def transition(self, target: NameT) -> bool:
        """Take the edge to target: run its actions, then write the new state
        name onto the context.

        One edge, never a path. A target the current state does not reach
        directly is simply refused, even when the graph could reach it in two
        moves — crossing a phase without a turn in it would skip that phase's
        actions, which only ever run per turn.

        Returns whether the move happened. A refusal is an ordinary answer, not
        an exception — the machine owns the edges, so "there is no such move"
        is something it knows rather than something it discovers.
        """
        if target not in self.available_transitions():
            return False
        source = self.current_state_name
        edge = self.graph.outgoing(source)[target]
        for action in edge.actions:
            await action(self._context, self._deps)
        self.enter_state(self._context, target)
        return True

    @property
    @abstractmethod
    def graph(self) -> Graph[ContextT, DepsT, EventT, NameT]:
        """This machine's graph, declared whole.

        State names are unique, a source/target pair appears at most once, and
        both endpoints of every edge are declared states. A graph that breaks
        any of the three is a mistake in the declaration, caught by the
        mechanics suite rather than raised at runtime.

        The same value every time: it does not read the context.
        """
        ...

    @abstractmethod
    def state_name_of(self, context: ContextT) -> NameT:
        """Read the current state name off the aggregate. The aggregate is the
        only durable carrier of the phase; the machine keeps no copy."""
        ...

    @abstractmethod
    def enter_state(self, context: ContextT, name: NameT) -> None:
        """Write a new state name onto the aggregate, in memory only."""
        ...


class StructuredStateMachine[ContextT, DepsT, EventT, NameT: StrEnum](
    StateMachine[ContextT, DepsT, EventT, NameT], ABC
):
    """A machine every one of whose states is a `StructuredState`.

    Narrows `current_state` only; the graph type is the shared one. That every
    declared state really is structured is a fact about the composition's
    graph, pinned by its suite — the same place graph well-formedness is held.

    Walking the flow is the caller's loop, not a method here: the machine holds
    no model-facing port. Per step the caller takes
    `current_state.output_without_model(context)` when it is not `None`, and
    otherwise sends `build_instruction()` and `current_state.output` to the
    model; it `apply`s the result either way, and stops when `advance`
    refuses. Every choice of route stays inside `advance`, so the
    loop is the same for any structured flow and knows none of them.
    """

    @property
    @override
    def current_state(self) -> StructuredState[ContextT, DepsT, EventT]: ...
