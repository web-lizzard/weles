from domain.capture.value_objects import MessageContent, Topic


class DeterministicTopicExtractionAdapter:
    async def extract(
        self,
        first_message: MessageContent,  # pyright: ignore[reportUnusedParameter]
    ) -> Topic:
        raise NotImplementedError
