from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from enum import StrEnum

from domain.shared.graph.model import Graph, State, Tool, ToolResult


class StateMachine[ContextT, EventT, NameT: StrEnum](ABC):
    """The mechanics of a phase graph, generic over the aggregate it carries,
    the event type a turn feeds it, and the enum naming its states.

    Knows nothing of any particular flow: a concrete machine declares one
    `Graph` and says where on the aggregate the current state name lives. Those
    are the only two things a composition supplies — everything else here is
    mechanics. The machine holds no model-facing port and never consumes a
    stream — the application owns the iterator and decides when a transition is
    evaluated. It never persists and never commits.
    """

    def __init__(self, context: ContextT) -> None:
        self._context: ContextT = context

    @property
    def context(self) -> ContextT:
        """The aggregate the machine carries. The caller reads what a turn
        touched from here — no separate record of changes is returned."""
        return self._context

    @property
    def current_state(self) -> State[ContextT, EventT]:
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

    async def apply(self, event: EventT) -> None:
        """Feed one event of a turn to the machine.

        Runs the actions the current state says this event warrants. Crosses no
        edge — a move is a separate, explicitly requested act.
        """
        for action in self.current_state.get_actions(self._context, event):
            await action(self._context, event)

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
            await action(self._context)
        self.enter_state(self._context, target)
        return True

    @property
    @abstractmethod
    def graph(self) -> Graph[ContextT, EventT, NameT]:
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
