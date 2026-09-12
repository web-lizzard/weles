from string import Formatter
from typing import Protocol

from pydantic import BaseModel, model_validator


class InstructionBlock(BaseModel, frozen=True):
    """One named piece of the prose a phase tells the model this turn.

    `name` is how the phase and its tests refer to the block; it is never shown
    to the model. `text` is the prose, authored in the domain's own vocabulary.
    Neither is a provider concept: turning a sequence of blocks into whatever
    instruction payload a library takes is the adapter's work (FR-09).

    `text` is finished prose. A block that carries a value from the turn is
    built through `rendered`, which interpolates and then keeps only the result.

    A block carries only what no other channel to the model already carries.
    A phase's tools reach the model through the provider's own tool channel and
    the turn's exchange reaches it as message history, so neither is repeated
    here: the instruction is what is left once those two are subtracted.

    It follows that a block never names a tool. A block that named one would
    claim to gate a capability it cannot gate — withholding the block leaves
    the tool offered and callable. The prohibition is on the tool's identity,
    not on its subject: prose may say what order the work goes in, because
    ordering is a fact about the task that no tool description can state on its
    own. What a tool is for belongs in `Tool.description`; what the agent
    should be doing with this turn belongs here. See
    `blocks-shape-tone-tools-shape-capability` in `discover-contracts-log.md`.
    """

    name: str
    text: str

    @classmethod
    def rendered(cls, name: str, template: str, **values: str) -> "InstructionBlock":
        """Build a block whose prose carries a value from the turn.

        The prose stays one piece of authored text with the value inside the
        sentence where it belongs, rather than a fixed line with data bolted
        after it — the phase's author decides where a topic name reads well,
        which no fixed arrangement can decide for every block.

        The template is what a test asserts against and the rendering is pure,
        so templated prose is exactly as pinnable as literal prose. What makes
        that true is the guard below, not the templating: without it, a renamed
        placeholder produces a block that is silently half-prose, and the only
        thing that would notice is the model.

        Rendering happens here and the result is stored. A block holds no
        template and no values of its own, so there is nothing left behind that
        a later edit could change the rendered text through — the same reason
        `Instruction.blocks` is a tuple.
        """
        placeholders = {
            field for _, field, _, _ in Formatter().parse(template) if field is not None
        }
        if "" in placeholders:
            raise ValueError(f"block {name!r} uses a positional placeholder")
        if placeholders != set(values):
            missing = sorted(placeholders - set(values))
            unused = sorted(set(values) - placeholders)
            message = "block {!r} template and values disagree: missing={} unused={}"
            raise ValueError(message.format(name, missing, unused))
        return cls(name=name, text=template.format(**values))


class Instruction(BaseModel, frozen=True):
    """The whole of what a phase tells the model this turn: an ordered sequence
    of blocks, and the names of the blocks that may not be missing from it.

    Order is the phase's decision and is preserved as given. Which optional
    blocks are present is also the phase's decision, taken from the turn's
    context — so conditionality lives in the domain, and a block the phase
    withholds is never rendered.

    `required` is the declaration FR-05 asks for, and it is carried on the
    instruction rather than beside it so that the completeness invariant is a
    property of the type. Any construction path enforces it; there is no path
    that produces an incomplete instruction for a dispatcher to guard against.

    `blocks` is exactly what the model is told, and there is no later filter.
    A phase decides what to withhold while it builds, never afterwards — a
    second gating step would let a required block be present at construction
    and suppressed after it, which is the one way FR-05's guard could be
    defeated. This is why the field is a tuple and not a list: a validated
    instruction whose blocks could still be removed would satisfy the guard
    and then stop satisfying it.

    Blocks are not independent of one another. Which ones are present, and what
    each says, is one decision about the turn taken as a whole, because a phase
    may withhold one block precisely because another is there. That decision
    belongs to `InstructionBuilder.build`, which returns the whole instruction
    at once, for the same reason `State.get_tools` is a method over the phase
    rather than a predicate per tool (`domain/shared/graph/model.py`).
    """

    blocks: tuple[InstructionBlock, ...]
    required: frozenset[str]

    @model_validator(mode="after")
    def _required_blocks_present(self) -> "Instruction":
        """Every required name appears among the blocks, and no name appears
        twice — the two invariants a sequence does not give for free."""
        names = [block.name for block in self.blocks]
        if len(names) != len(set(names)):
            raise ValueError("instruction declares a block name twice")
        missing = self.required - set(names)
        if missing:
            raise ValueError(
                f"instruction is missing required blocks: {sorted(missing)}"
            )
        return self


class InstructionBuilder[ContextT](Protocol):
    """How a phase constructs its instruction from the turn it already holds.

    A domain abstraction, not a port and not an adapter. `build` is
    synchronous and reaches nothing: an instruction describes the turn as it
    stands, and fetching to enrich it would buy staleness with latency.

    `required` is declared here as well as carried on the result, because what
    a phase's instruction can never omit is a fact about the phase and stays
    inspectable without a context — the same reason `State.tools` is an
    unfiltered inventory beside `State.get_tools`.
    """

    @property
    def required(self) -> frozenset[str]: ...

    def build(self, context: ContextT) -> Instruction: ...
