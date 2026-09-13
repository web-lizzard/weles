import re
from typing import cast

from pydantic import BaseModel

from domain.distill.instructions import CANDIDATES, GAPS, NOTE
from domain.distill.run import CardsProposed, CardsReviewed, DuplicatesFound
from domain.distill.value_objects import (
    CandidateRef,
    CardProposal,
    CardVerdict,
    ReviewGrade,
)
from domain.shared.instruction.model import Instruction

_BLOCK_SEPARATOR_PATTERN = re.compile(r"\n\s*\n")
_SENTENCE_END_PATTERN = re.compile(r"[.?!]")
_CANDIDATE_LINE_PATTERN = re.compile(r"^(c\d+):")

_FABRICATED_FRONT = "What is the capital of Wonderland?"
_FABRICATED_BACK = (
    "There is no such capital; this proposal is a deliberate control card"
    " used to exercise the ungrounded-discard path end to end."
)
_FABRICATED_QUOTE = "no note is ever expected to contain this exact sentinel phrase"

_REVIEW_REASONING = (
    "Grounded in the note, self-contained, and worth keeping at the sound bar."
)


class DeterministicStructuredTaskAdapter:
    async def complete[OutputT: BaseModel](
        self,
        instruction: Instruction,
        output: type[OutputT],
    ) -> OutputT:
        if output is CardsProposed:
            return cast(OutputT, _cards_proposed(instruction))
        if output is CardsReviewed:
            return cast(OutputT, _cards_reviewed(instruction))
        if output is DuplicatesFound:
            return cast(OutputT, DuplicatesFound(groups=[]))
        raise TypeError(f"unsupported structured output type: {output!r}")


def _cards_proposed(instruction: Instruction) -> CardsProposed:
    if _block_text(instruction, GAPS) is not None:
        return CardsProposed(proposals=[])
    note_text = _block_text(instruction, NOTE)
    if note_text is None:
        raise ValueError("instruction is missing NOTE block")
    proposals = [
        proposal
        for block in _paragraph_blocks(note_text)
        if (proposal := _proposal_from_block(block)) is not None
    ]
    proposals.append(
        CardProposal(
            front=_FABRICATED_FRONT,
            back=_FABRICATED_BACK,
            quote=_FABRICATED_QUOTE,
        )
    )
    return CardsProposed(proposals=proposals)


def _cards_reviewed(instruction: Instruction) -> CardsReviewed:
    candidates_text = _block_text(instruction, CANDIDATES)
    if candidates_text is None:
        raise ValueError("instruction is missing CANDIDATES block")
    verdicts = [
        CardVerdict(ref=ref, grade=ReviewGrade.SOUND, reasoning=_REVIEW_REASONING)
        for ref in _refs_from_candidates(candidates_text)
    ]
    return CardsReviewed(verdicts=verdicts)


def _block_text(instruction: Instruction, name: str) -> str | None:
    for block in instruction.blocks:
        if block.name == name:
            return block.text
    return None


def _paragraph_blocks(content: str) -> list[str]:
    return [block for block in _BLOCK_SEPARATOR_PATTERN.split(content) if block.strip()]


def _proposal_from_block(block: str) -> CardProposal | None:
    match = _SENTENCE_END_PATTERN.search(block)
    split_at = match.end() if match else _midpoint_word_boundary(block)
    front = block[:split_at].strip()
    back = block[split_at:].strip()
    if not back:
        return None
    return CardProposal(front=front, back=back, quote=block)


def _midpoint_word_boundary(block: str) -> int:
    """Where to split a block with no sentence-ending punctuation: the first
    space at or after its midpoint, so front and back both come back
    non-empty instead of the whole block collapsing into `front`."""
    midpoint = len(block) // 2
    space = block.find(" ", midpoint)
    return space if space != -1 else midpoint


def _refs_from_candidates(text: str) -> list[CandidateRef]:
    refs: list[CandidateRef] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = _CANDIDATE_LINE_PATTERN.match(stripped)
        if match:
            refs.append(CandidateRef(value=match.group(1)))
    return refs
