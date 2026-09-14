from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import final, override

from domain.capture.coverage import reading_of
from domain.capture.turn import CaptureTurn
from domain.capture.value_objects import CoverageReading
from domain.shared.instruction.model import (
    Instruction,
    InstructionBlock,
    InstructionBuilder,
)

FLOW = "flow"
LANGUAGE = "language"
TASK = "task"
SESSION_TOPIC = "session_topic"
COVERAGE_TREND = "coverage_trend"
HANDOFF = "handoff"
DRAFT_STATE = "draft_state"
"""The names of capture's blocks.

Named constants rather than inline strings because a phase's builder declares
its required set by name and its tests assert presence by name — places that
must agree, and a typo in any of them would otherwise pass construction.
"""


class CaptureInstructionBuilder(InstructionBuilder[CaptureTurn], ABC):
    """The shape every capture phase's builder takes: a general part it does
    not author, and a phase part it does.

    **The general part is required of capture, not of each phase separately.**
    `FLOW` says what a capture session is for — including speaking Socratically
    to the user while conversing — and `LANGUAGE` constrains how the agent
    answers; both are true in every phase, so no phase is given the choice
    to drop them. `required` unions the general floor into whatever the phase
    declares, which is why `phase_required` names only the phase's own — a
    subclass has no way to subtract, and a phase added later inherits the floor
    without anyone remembering to write it.

    The general blocks come first and the phase's follow. Order is what the
    reader meets first, and what the flow is has to be established before what
    this turn of it asks for.

    A phase decides its blocks as a set, in `phase_blocks`, never as a predicate
    per block — see `Instruction`.
    """

    @property
    @abstractmethod
    def phase_required(self) -> frozenset[str]:
        """The blocks this phase's own instruction can never omit. The general
        floor is not restated here; `required` adds it."""
        ...

    @abstractmethod
    def phase_blocks(self, context: CaptureTurn) -> tuple[InstructionBlock, ...]:
        """This phase's blocks for this turn, in the order the phase wants them
        read. Excludes the general part."""
        ...

    @property
    @final
    @override
    def required(self) -> frozenset[str]:
        return _GENERAL_REQUIRED | self.phase_required

    @final
    @override
    def build(self, context: CaptureTurn) -> Instruction:
        """The general blocks, then `phase_blocks`, as one `Instruction` whose
        `required` is this builder's own.

        Final, and the reason is the one duplication this session had left
        open. `required` is declared on the builder and carried on the
        `Instruction`, and a phase free to build its own instruction could pass
        a required set that disagrees with the one it advertises — satisfying a
        guard against a declaration nobody else holds. Composing here means the
        two can only ever be the same value, so the second copy is a copy and
        never a second opinion.

        A phase overrides `phase_blocks` and `phase_required`, never this.
        """
        blocks = (_FLOW, _LANGUAGE, *self.phase_blocks(context))
        return Instruction(blocks=blocks, required=self.required)


class ConversingInstructionBuilder(CaptureInstructionBuilder):
    """What the agent is told while the session talks its topic through.

    Phase-required: `TASK` — true of every conversing turn.

    Optional, each present only when it has something to say:

    - `SESSION_TOPIC` — present if `turn.session.topic is not None`. Before the
      session is named there is no topic to hold the agent to, and the exchange
      itself already shows the session is new, so the block is absent rather
      than saying so in prose.
    - `COVERAGE_TREND` — present if the session holds enough assessments for a
      reading to exist. This is the block FR-03 rests on: the reading is computed
      in the domain and crosses the port as a word, never as the float. It
      carries the encouragement with the reading, because a word on its own would
      be telemetry again.
    """

    @property
    @override
    def phase_required(self) -> frozenset[str]:
        return frozenset({TASK})

    @override
    def phase_blocks(self, context: CaptureTurn) -> tuple[InstructionBlock, ...]:
        blocks: list[InstructionBlock] = [_CONVERSING_TASK]
        if context.session.topic is not None:
            blocks.append(
                InstructionBlock.rendered(
                    SESSION_TOPIC,
                    _SESSION_TOPIC_TEMPLATE,
                    topic=context.session.topic.value,
                )
            )
        reading = reading_of(context.session.assessments)
        if reading is not None:
            blocks.append(
                InstructionBlock(
                    name=COVERAGE_TREND,
                    text=_COVERAGE_READING_PROSE[reading],
                )
            )
        return tuple(blocks)


class DraftingInstructionBuilder(CaptureInstructionBuilder):
    """What the agent is told while it writes the note.

    Phase-required: `TASK` and `DRAFT_STATE`. The draft's state is required
    rather than optional because there is always something true to say about it,
    and the empty case is the one that matters most: appending content to a
    draft with no topic raises `DraftTopicMissingError`
    (`domain/capture/graph.py`), so the ordering has to be told rather than
    discovered by failing.

    Optional:

    - `HANDOFF` — present only on the turn a drafting pass opens, which the turn
      shows as `context.draft is None`. It is what the agent says as it takes
      over; on later turns of the same pass it would announce again something
      already announced.

    A second drafting pass is not a fresh one. `turn.session.note_id is not None`
    with no draft in hand means a note already exists and this pass revises it,
    and `DRAFT_STATE` says so — FR-02 makes that reachable, and a block that
    spoke only of writing a new note would be false there.
    """

    @property
    @override
    def phase_required(self) -> frozenset[str]:
        return frozenset({TASK, DRAFT_STATE})

    @override
    def phase_blocks(self, context: CaptureTurn) -> tuple[InstructionBlock, ...]:
        blocks: list[InstructionBlock] = [_DRAFTING_TASK]
        if context.draft is not None:
            draft = context.draft
            topic = (
                draft.topic.label.value
                if draft.topic is not None
                else "the session's topic"
            )
            tags = ", ".join(tag.label.value for tag in draft.tags) or "none yet"
            blocks.append(
                InstructionBlock.rendered(
                    DRAFT_STATE,
                    _DRAFT_STATE_UNDERWAY_TEMPLATE,
                    topic=topic,
                    tags=tags,
                )
            )
        elif context.session.note_id is not None:
            topic = (
                context.session.topic.value
                if context.session.topic is not None
                else "the note's topic"
            )
            blocks.append(
                InstructionBlock.rendered(
                    DRAFT_STATE,
                    _DRAFT_STATE_REVISING_TEMPLATE,
                    topic=topic,
                )
            )
        else:
            blocks.append(_DRAFT_STATE_EMPTY)
        if context.draft is None and context.session.note_id is None:
            blocks.append(_HANDOFF)
        return tuple(blocks)


_GENERAL_REQUIRED = frozenset({FLOW, LANGUAGE})

_FLOW = InstructionBlock(
    name=FLOW,
    text=(
        "You are in a capture session. Its purpose is to help the user work "
        "through a topic until what they understand is genuinely their own — "
        "their reasoning and their words — and later to turn that into a note "
        "they keep. While you are conversing, speak to the user Socratically: "
        "explain what they need to grasp, then ask questions that help them "
        "think it through instead of handing them finished conclusions. The "
        "session belongs to the user throughout; you guide and probe, and you "
        "do not decide on their behalf when it is done."
    ),
)

_LANGUAGE = InstructionBlock(
    name=LANGUAGE,
    text="Reply in the language the user is writing in.",
)

_CONVERSING_TASK = InstructionBlock(
    name=TASK,
    text=(
        "On this turn, stay with the session's topic. When the user needs a "
        "concept, explain it plainly; then ask focused questions that surface "
        "what they already understand and where their grasp is still shaky. "
        "Judge how fully the topic has been covered as you go. When the user "
        "asks for the note or a draft, call signal_drafting_consent on this "
        "turn. That turn's chat is at most one short sentence that you are "
        "starting the note (or nothing) — then drafting continues in a "
        "separate step that owns the note body. Do not ask questions, offer "
        "templates, or describe how the note should look."
    ),
)

_DRAFTING_TASK = InstructionBlock(
    name=TASK,
    text=(
        "Write the note from what this session captured. It is the user's own "
        "material organised, not a transcript and not a summary of your reading "
        "of it. Name its topic before writing its body. Put the body only in "
        "propose_note_content, never in the chat reply."
    ),
)

_HANDOFF = InstructionBlock(
    name=HANDOFF,
    text=(
        "Your chat reply on this turn is one brief sentence that you are "
        "starting the note from the session, in the user's language — then use "
        "the note tools. Do not ask questions or describe structure in chat."
    ),
)


_SESSION_TOPIC_TEMPLATE = (
    "This session is about {topic}. Hold the conversation to it, and say so "
    "plainly if the user moves somewhere else."
)

_DRAFT_STATE_EMPTY = InstructionBlock(
    name=DRAFT_STATE,
    text=(
        "Nothing of the note exists yet. It needs a topic before it can have a "
        "body, so name the topic first and write the body after."
    ),
)

_DRAFT_STATE_UNDERWAY_TEMPLATE = (
    "The note's topic is {topic}, and its tags so far are {tags}. Continue the "
    "body from what is already written rather than starting it again."
)

_DRAFT_STATE_REVISING_TEMPLATE = (
    "This session already wrote a note, on {topic}, and you are revising it "
    "rather than writing a new one. What you produce replaces what it holds, so "
    "carry over what still belongs."
)
"""The templates behind the blocks whose prose carries a value.

Module constants, exactly like the literal blocks above, so that authored prose
lives in one place whether or not a value goes into it. A builder picks a
template and supplies values; it never writes prose of its own.
"""

_COVERAGE_READING_PROSE: Mapping[CoverageReading, str] = {
    CoverageReading.EARLY: (
        "The topic has barely been opened. Keep explaining and questioning "
        "Socratically, and do not raise finishing the session at all — there "
        "is not yet enough here for that question to be fair."
    ),
    CoverageReading.DEEPENING: (
        "The conversation is covering more ground each turn. It is working; "
        "keep going, and let the user know that wrapping up is becoming "
        "available without pressing them towards it."
    ),
    CoverageReading.WIDENING: (
        "The user has opened ground that was not in view before, so the topic "
        "grew. This is the conversation working, not slipping. Follow the new "
        "ground and leave the question of finishing alone."
    ),
    CoverageReading.SETTLED: (
        "Little new has arrived for a while and the topic looks well covered. "
        "Say so, and encourage the user to wrap the session up."
    ),
}
"""What the agent is told for each reading. FR-03's policy in full.

A mapping over a closed `StrEnum`, so a reading added later without prose is a
missing key a suite can walk the enum to find — the exhaustiveness this
repository already recovers by test rather than by type
(`context/foundation/rules/exceptions.md`).
"""
