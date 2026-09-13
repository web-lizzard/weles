import re

from pydantic import BaseModel
from pydantic_ai import Agent

from adapters.out.llm.tracing import observation
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
        block_texts = [block.text for block in instruction.blocks]
        with observation(
            _snake_case(output.__name__),
            observation_type="generation",
            input_value=block_texts,
        ) as recorder:
            recorder.record_model(self._model_name)
            result = await self._agent.run(
                instructions=block_texts,
                output_type=output,
            )
            usage = result.usage
            recorder.record_usage(
                {
                    "input": usage.input_tokens,
                    "output": usage.output_tokens,
                }
            )
            recorder.record_output(result.output.model_dump(mode="json"))
            return result.output


def _snake_case(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
