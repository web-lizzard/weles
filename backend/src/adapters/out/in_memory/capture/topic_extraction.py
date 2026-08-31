from domain.capture.value_objects import MessageContent, SessionTopic

_MAX_TOPIC_WORDS = 8
_DEFAULT_TOPIC = "Untitled capture session"


class DeterministicTopicExtractionAdapter:
    async def extract(self, first_message: MessageContent) -> SessionTopic:
        words = first_message.value.strip().split()
        value = " ".join(words[:_MAX_TOPIC_WORDS]) or _DEFAULT_TOPIC
        return SessionTopic(value=value)
