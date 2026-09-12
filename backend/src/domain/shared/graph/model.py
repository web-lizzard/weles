from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Mapping, Sequence
from enum import StrEnum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, model_validator

type Condition[ContextT, EventT] = Callable[[ContextT, EventT], bool]
"""Whether an edge may be taken. Reads the context and the event that is being
applied."""

type Action[ContextT, EventT] = Callable[[ContextT, EventT], Awaitable[None]]
"""Deterministic domain work. May mutate the context in memory and may call a
domain port; never persists and never commits."""

type EdgeCondition[ContextT] = Callable[[ContextT], bool]
"""Whether an edge may be taken after a turn segment. Reads only the context —
no event requests the move."""

type EdgeAction[ContextT] = Callable[[ContextT], Awaitable[None]]
"""Deterministic domain work run when an edge is taken. May mutate the context
in memory and may call a domain port; never persists and never commits."""


class ToolResult(BaseModel, frozen=True):
    """The base of every tool's return model.

    A concrete result is a child that pins `tool` to a `Literal`, so the
    results a state's tools can produce form a discriminated union — the same
    shape `ReplyChunk` already uses in `application/capture/value_objects.py`.
    A child must repeat `frozen=True`, or pydantic refuses the subclass.

    Invariant: a result's pinned `tool` equals the `name` of the `Tool` that
    declares it. Nothing else identifies which tool a result came back from.
    """

    tool: str


type ToolArguments = Mapping[str, object]
"""What the model sent along with a tool call. Ephemeral as far as the domain
is concerned: the mechanics carry the bag and never model it, and a handler
that needs structure parses it into a shape of its own."""

type ToolHandler[ContextT, ResultT: ToolResult] = Callable[
    [ContextT, ToolArguments], Awaitable[ResultT]
]
"""What a tool does when the model calls it: reads the context and the
arguments, computes, and returns its result. Never mutates the context and
never persists."""


class Tool[ContextT, ResultT: ToolResult](BaseModel, frozen=True):
    """The model-facing surface of a state: proposes, reads, computes; never
    changes the context.

    `name`, `description` and `result` are what the model is shown — rendering
    them as a provider-facing tool definition is slice S-04's. `handler` is
    what runs when the model picks it, and it receives the context and the
    arguments the model sent.

    A tool carries no availability of its own. Whether it is offered is the
    state's decision; a tool the state withholds is never rendered and so can
    never be called.
    """

    name: str
    description: str
    result: type[ResultT]
    handler: ToolHandler[ContextT, ResultT]

    @model_validator(mode="after")
    def _result_discriminator_matches_name(self) -> "Tool[ContextT, ResultT]":
        """A result's pinned `tool` default must equal this tool's `name` —
        otherwise the discriminator cannot identify which tool produced it."""
        declared_tool = self.result.model_construct().tool
        if declared_tool != self.name:
            message = "tool result discriminator {!r} does not match name {!r}"
            raise ValueError(message.format(declared_tool, self.name))
        return self


class State[ContextT, EventT](ABC):
    """One node of the graph: a phase a context can sit in for many turns.

    A state declares its full inventory of tools and actions, and decides per
    turn which of them the context is currently eligible for. Both decisions
    are methods rather than per-item predicates, because eligibility is a
    statement about the phase as a whole — a state may withhold one tool
    because another has already done its work, which a list of independent
    predicates cannot express.

    A state does not carry its own name. It is named by the key it sits under
    in a `Graph`, so the two can never disagree.
    """

    @property
    @abstractmethod
    def tools(self) -> Sequence[Tool[ContextT, ToolResult]]:
        """Every tool this state can ever offer, unfiltered. The inventory, so
        that what a phase is capable of stays inspectable without a context."""
        ...

    @property
    @abstractmethod
    def actions(self) -> Sequence[Action[ContextT, EventT]]:
        """Every action this state can ever run, unfiltered."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """What a model reads when choosing where to go next from this phase."""
        ...

    def get_tools(self, context: ContextT) -> Sequence[Tool[ContextT, ToolResult]]:
        """The tools to offer the model this turn, recomputed from the context
        every time so a tool whose work is already done is not offered again.

        Defaults to the whole inventory; a state that filters overrides this.
        """
        _ = context
        return self.tools

    def get_actions(
        self, context: ContextT, event: EventT
    ) -> Sequence[Action[ContextT, EventT]]:
        """The actions this event warrants running against the context.

        Defaults to the whole inventory; a state that filters overrides this.
        """
        _ = context, event
        return self.actions


class Transition[ContextT, EventT](BaseModel, frozen=True):
    """One edge of the graph: what it takes to make a move, and what happens
    when it is made.

    It carries no source and no target. Those are the keys it sits under in a
    `Graph`, so an edge cannot claim endpoints it is not filed under.
    """

    guard: EdgeCondition[ContextT] | None = None
    actions: Sequence[EdgeAction[ContextT]] = ()


class Graph[ContextT, EventT, NameT: StrEnum](BaseModel, frozen=True):
    """A whole phase graph as one artifact: its states by name, and its edges
    by source and then target.

    Keying rather than listing is what makes the declaration's invariants
    structural. A mapping cannot hold two states under one name, and a nested
    mapping cannot hold two edges for one source/target pair — so neither is a
    rule anything has to enforce or test. What is left to check is only that
    every endpoint names a declared state, and that no edge returns to its own
    state.

    Static by construction. A graph is never derived from a context — which
    moves are legal has to be a property of the phase alone, or "legal from
    here" stops meaning anything and no test can pin it down.

    It is a directed graph and it cycles: FR-02 requires conversing and note
    drafting to reach each other in both directions, so there is no root and no
    tree form of it.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)

    states: Mapping[NameT, State[ContextT, EventT]]
    transitions: Mapping[NameT, Mapping[NameT, Transition[ContextT, EventT]]]

    def outgoing(self, source: NameT) -> Mapping[NameT, Transition[ContextT, EventT]]:
        """Every edge leaving this state, by target. Guards are not evaluated:
        this is what the graph permits in principle, not what is permitted now.

        Empty for a state with no outgoing edge, rather than absent.
        """
        return self.transitions.get(source, {})

    def is_terminal(self, name: NameT) -> bool:
        """Whether this state has no outgoing edge at all.

        The singular of `terminal_states`, and structurally terminal in the
        same limited sense — see there.
        """
        return not self.outgoing(name)

    @property
    def terminal_states(self) -> frozenset[NameT]:
        """Every declared state that `is_terminal` — states a context could
        enter and never leave.

        The set form is what a suite asserts against, because a phase added
        later is caught without anyone remembering to extend the assertion;
        `is_terminal` is what a caller asks about one state it already holds.

        Structurally terminal only. A state with an outgoing edge whose guard
        can never pass is just as inescapable and is not reported here, because
        no static reading of a graph can tell an unsatisfiable guard from one
        that has simply not been satisfied yet. `frame.md` constrains that half
        separately, and only a test written against a specific guard can hold
        it.

        A query, not a rule: a terminal state is legitimate in some graphs, so
        the mechanics only report them. A graph that forbids them, as capture's
        does under FR-02, asserts this is empty in its own suite.
        """
        return frozenset(name for name in self.states if self.is_terminal(name))

    def reachable_from(self, source: NameT) -> frozenset[NameT]:
        """Every state reachable from source by following one or more edges,
        guards not evaluated.

        This is the only sense in which the graph answers a question about
        several moves at once. Taking several moves is not offered: a move is
        one edge, decided per turn, so that entering a phase always means a
        turn happened in it.
        """
        reached: set[NameT] = set()
        frontier = list(self.outgoing(source))
        while frontier:
            name = frontier.pop()
            if name in reached:
                continue
            reached.add(name)
            frontier.extend(
                target for target in self.outgoing(name) if target not in reached
            )
        return frozenset(reached)

    @model_validator(mode="after")
    def _validate_edges(self) -> "Graph[ContextT, EventT, NameT]":
        """Every endpoint is a declared state, and no edge returns to its own
        state — the two invariants the keying does not give for free."""
        for source, targets in self.transitions.items():
            if source not in self.states:
                raise ValueError(f"edge source {source} is not a declared state")
            for target in targets:
                if target not in self.states:
                    raise ValueError(f"edge target {target} is not a declared state")
                if source == target:
                    raise ValueError(
                        f"edge {source} -> {target} returns to its own state"
                    )
        return self
