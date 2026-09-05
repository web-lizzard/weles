import re

from application.distill.value_objects import CardProposal
from domain.distill.value_objects import NoteContent

_BLOCK_SEPARATOR_PATTERN = re.compile(r"\n\s*\n")
_SENTENCE_END_PATTERN = re.compile(r"[.?!]")

_FABRICATED_FRONT = "What is the capital of Wonderland?"
_FABRICATED_BACK = (
    "There is no such capital; this proposal is a deliberate control card"
    " used to exercise the ungrounded-discard path end to end."
)
_FABRICATED_QUOTE = "no note is ever expected to contain this exact sentinel phrase"


class DeterministicCardGenerationAdapter:
    async def generate(self, content: NoteContent) -> list[CardProposal]:
        proposals = [
            proposal
            for block in _blocks(content.value)
            if (proposal := _proposal_from_block(block)) is not None
        ]
        proposals.append(
            CardProposal(
                front=_FABRICATED_FRONT,
                back=_FABRICATED_BACK,
                quote=_FABRICATED_QUOTE,
            )
        )
        return proposals


def _blocks(content: str) -> list[str]:
    return [block for block in _BLOCK_SEPARATOR_PATTERN.split(content) if block.strip()]


def _proposal_from_block(block: str) -> CardProposal | None:
    match = _SENTENCE_END_PATTERN.search(block)
    split_at = match.end() if match else len(block)
    front = block[:split_at].strip()
    back = block[split_at:].strip()
    if not back:
        return None
    return CardProposal(front=front, back=back, quote=block)
