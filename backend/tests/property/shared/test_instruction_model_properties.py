# pyright: reportUnusedParameter=false
"""Property tests over the shared instruction model (instruction-context phase 1)."""

import re
from string import Formatter

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from domain.shared.instruction.model import Instruction, InstructionBlock

_named_placeholder = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def _expected_placeholders(template: str) -> set[str]:
    return set(_named_placeholder.findall(template))


@st.composite
def valid_rendered_inputs(draw: st.DrawFn) -> tuple[str, str, dict[str, str]]:
    """Template uses only named placeholders; values keys match exactly."""
    keys = draw(
        st.lists(
            st.from_regex(r"[a-zA-Z_][a-zA-Z0-9_]{0,8}", fullmatch=True),
            min_size=0,
            max_size=5,
            unique=True,
        )
    )
    safe = st.text(alphabet=st.characters(blacklist_characters="{}"), max_size=20)
    values = {
        key: draw(
            st.text(alphabet=st.characters(blacklist_characters="{}"), max_size=40)
        )
        for key in keys
    }
    template = draw(safe)
    for key in keys:
        template += f"{{{key}}}"
    template += draw(safe)
    _ = assume(_expected_placeholders(template) == set(values))
    parsed = {f for _, f, _, _ in Formatter().parse(template) if f is not None}
    _ = assume("" not in parsed)
    name = draw(st.from_regex(r"[A-Z][A-Z0-9_]{0,12}", fullmatch=True))
    return name, template, values


@given(payload=valid_rendered_inputs())
@settings(max_examples=100, deadline=None)
def test_rendered_text_matches_str_format_for_valid_templates(
    payload: tuple[str, str, dict[str, str]],
) -> None:
    name, template, values = payload
    block = InstructionBlock.rendered(name, template, **values)
    assert block.name == name
    assert block.text == template.format(**values)


@st.composite
def instruction_with_unique_names(
    draw: st.DrawFn,
) -> tuple[frozenset[str], tuple[InstructionBlock, ...]]:
    count = draw(st.integers(min_value=0, max_value=8))
    names = draw(
        st.lists(
            st.from_regex(r"[A-Z][A-Z0-9_]{0,10}", fullmatch=True),
            min_size=count,
            max_size=count,
            unique=True,
        )
    )
    blocks = tuple(
        InstructionBlock(name=name, text=draw(st.text(min_size=1, max_size=80)))
        for name in names
    )
    if names:
        required = draw(st.frozensets(st.sampled_from(names), max_size=len(names)))
    else:
        required: frozenset[str] = frozenset()
    return required, blocks


@given(spec=instruction_with_unique_names())
@settings(max_examples=100, deadline=None)
def test_instruction_constructs_iff_required_names_are_among_unique_block_names(
    spec: tuple[frozenset[str], tuple[InstructionBlock, ...]],
) -> None:
    required, blocks = spec
    names = [block.name for block in blocks]
    unique = len(names) == len(set(names))
    missing = required - set(names)

    if not unique or missing:
        try:
            _ = Instruction(required=required, blocks=blocks)
        except ValueError:
            return
        raise AssertionError(
            "expected ValueError for duplicate names or missing required"
        )
    instruction = Instruction(required=required, blocks=blocks)
    assert instruction.required == required
    assert instruction.blocks == blocks
    assert isinstance(instruction.blocks, tuple)


@given(
    blocks=st.lists(
        st.builds(
            InstructionBlock,
            name=st.from_regex(r"[A-Z][A-Z0-9_]{0,8}", fullmatch=True),
            text=st.text(min_size=1, max_size=60),
        ),
        min_size=2,
        max_size=6,
    ).filter(lambda items: len({b.name for b in items}) < len(items)),
)
@settings(max_examples=100, deadline=None)
def test_instruction_rejects_duplicate_block_names(
    blocks: list[InstructionBlock],
) -> None:
    required = frozenset({blocks[0].name})
    try:
        _ = Instruction(required=required, blocks=tuple(blocks))
    except ValueError as exc:
        assert "twice" in str(exc)
        return
    raise AssertionError("expected duplicate-name ValueError")
