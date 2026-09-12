from typing import override

from domain.shared.instruction.model import (
    Instruction,
    InstructionBlock,
    InstructionBuilder,
)


class GraphTestInstructionBuilder(InstructionBuilder[object]):
    @property
    @override
    def required(self) -> frozenset[str]:
        return frozenset({"stub"})

    @override
    def build(self, context: object) -> Instruction:
        _ = context
        return Instruction(
            blocks=(InstructionBlock(name="stub", text="stub"),),
            required=frozenset({"stub"}),
        )


GRAPH_TEST_INSTRUCTION_BUILDER = GraphTestInstructionBuilder()
