from pydantic import BaseModel

from domain.shared.instruction.model import Instruction


class DeterministicStructuredTaskAdapter:
    async def complete[OutputT: BaseModel](
        self,
        instruction: Instruction,
        output: type[OutputT],
    ) -> OutputT:
        _ = instruction, output
        raise NotImplementedError
