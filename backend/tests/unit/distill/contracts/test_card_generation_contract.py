from collections.abc import Callable
from typing import cast

import pytest

from adapters.out.in_memory.distill.card_generation import (
    DeterministicCardGenerationAdapter,
)
from adapters.out.in_memory.distill.note_document_parser import (
    MarkdownNoteDocumentParser,
)
from application.distill.ports import CardGeneration
from application.distill.value_objects import CardProposal
from domain.distill.value_objects import NoteContent

_IMPLEMENTATIONS: list[Callable[[], CardGeneration]] = [
    cast(Callable[[], CardGeneration], DeterministicCardGenerationAdapter),
]

_PARSER = MarkdownNoteDocumentParser()

_TWO_BLOCK_NOTE = NoteContent(
    value=(
        "TCP begins the handshake. The client sends a SYN packet first.\n"
        "\n"
        "The server responds with SYN-ACK. It waits for the final ACK.\n"
    )
)

_SINGLE_SENTENCE_NOTE = NoteContent(value="Only one sentence appears here.")


async def _resolves(content: NoteContent, proposal: CardProposal) -> bool:
    return await _PARSER.resolves(content, proposal.quote)


@pytest.mark.parametrize("make_generator", _IMPLEMENTATIONS, ids=["deterministic"])
async def test_every_proposal_has_non_empty_sides(
    make_generator: Callable[[], CardGeneration],
) -> None:
    generator = make_generator()

    proposals = await generator.generate(_TWO_BLOCK_NOTE)

    assert proposals
    assert all(proposal.front.strip() for proposal in proposals)
    assert all(proposal.back.strip() for proposal in proposals)


@pytest.mark.parametrize("make_generator", _IMPLEMENTATIONS, ids=["deterministic"])
async def test_every_block_derived_quote_resolves_against_the_note(
    make_generator: Callable[[], CardGeneration],
) -> None:
    generator = make_generator()

    proposals = await generator.generate(_TWO_BLOCK_NOTE)
    block_derived = proposals[:-1]

    assert block_derived
    for proposal in block_derived:
        assert await _resolves(_TWO_BLOCK_NOTE, proposal) is True


@pytest.mark.parametrize("make_generator", _IMPLEMENTATIONS, ids=["deterministic"])
async def test_exactly_one_proposal_does_not_resolve(
    make_generator: Callable[[], CardGeneration],
) -> None:
    generator = make_generator()

    proposals = await generator.generate(_TWO_BLOCK_NOTE)
    unresolved = [
        proposal
        for proposal in proposals
        if not await _resolves(_TWO_BLOCK_NOTE, proposal)
    ]

    assert len(unresolved) == 1


@pytest.mark.parametrize("make_generator", _IMPLEMENTATIONS, ids=["deterministic"])
async def test_generation_is_deterministic_for_the_same_content(
    make_generator: Callable[[], CardGeneration],
) -> None:
    generator = make_generator()

    first = await generator.generate(_TWO_BLOCK_NOTE)
    second = await generator.generate(_TWO_BLOCK_NOTE)

    assert first
    assert first == second


@pytest.mark.parametrize("make_generator", _IMPLEMENTATIONS, ids=["deterministic"])
async def test_a_single_sentence_note_yields_only_the_fabricated_proposal(
    make_generator: Callable[[], CardGeneration],
) -> None:
    generator = make_generator()

    proposals = await generator.generate(_SINGLE_SENTENCE_NOTE)

    assert len(proposals) == 1
    assert await _resolves(_SINGLE_SENTENCE_NOTE, proposals[0]) is False
