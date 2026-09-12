import pytest

from domain.shared.instruction.model import Instruction, InstructionBlock


def test_rendered_stores_interpolated_text_when_placeholders_match_values() -> None:
    block = InstructionBlock.rendered(
        "TOPIC",
        "Stay with {topic} until the user moves on.",
        topic="billing",
    )

    assert block.name == "TOPIC"
    assert block.text == "Stay with billing until the user moves on."


@pytest.mark.parametrize(
    ("template", "values", "match"),
    [
        (
            "Focus on {topic}.",
            {},
            "missing",
        ),
        (
            "Focus on {topic}.",
            {"topic": "billing", "extra": "unused"},
            "unused",
        ),
        (
            "Focus on {}.",
            {"topic": "billing"},
            "positional",
        ),
    ],
)
def test_rendered_raises_when_template_and_values_disagree(
    template: str,
    values: dict[str, str],
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        _ = InstructionBlock.rendered("TOPIC", template, **values)


def test_instruction_raises_when_a_required_block_name_is_missing() -> None:
    role = InstructionBlock(name="ROLE", text="You are a capture assistant.")

    with pytest.raises(ValueError, match="missing required blocks"):
        _ = Instruction(required=frozenset({"ROLE", "TOPIC"}), blocks=(role,))


def test_instruction_raises_when_two_blocks_share_a_name() -> None:
    first = InstructionBlock(name="ROLE", text="First.")
    second = InstructionBlock(name="ROLE", text="Second.")

    with pytest.raises(ValueError, match="twice"):
        _ = Instruction(required=frozenset({"ROLE"}), blocks=(first, second))


def test_instruction_constructs_when_required_names_are_present() -> None:
    role = InstructionBlock(name="ROLE", text="You are a capture assistant.")
    topic = InstructionBlock(name="TOPIC", text="The topic is billing.")

    instruction = Instruction(
        required=frozenset({"ROLE", "TOPIC"}),
        blocks=(role, topic),
    )

    assert instruction.blocks == (role, topic)
    assert instruction.required == frozenset({"ROLE", "TOPIC"})


def test_instruction_blocks_is_a_tuple_that_cannot_grow_after_construction() -> None:
    role = InstructionBlock(name="ROLE", text="You are a capture assistant.")
    instruction = Instruction(required=frozenset({"ROLE"}), blocks=(role,))

    assert isinstance(instruction.blocks, tuple)
    assert not hasattr(instruction.blocks, "append")
