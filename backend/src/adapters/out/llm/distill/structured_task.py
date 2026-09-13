from pydantic import BaseModel
from pydantic_ai import Agent

from domain.shared.instruction.model import Instruction


class PydanticAiStructuredTaskAdapter:
    _agent: Agent
    _model_name: str

    def __init__(self, agent: Agent, model_name: str) -> None:
        self._agent = agent
        self._model_name = model_name

    async def complete[OutputT: BaseModel](
        self,
        instruction: Instruction,
        output: type[OutputT],
    ) -> OutputT:
        _ = instruction, output
        raise NotImplementedError
