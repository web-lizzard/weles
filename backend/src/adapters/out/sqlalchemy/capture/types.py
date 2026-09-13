from typing import Any, cast, override

from domain.capture.value_objects import (
    ConversationRequest,
    Coverage,
    DraftingConsent,
    Label,
    MessageContent,
    MessageId,
    NoteContent,
    NoteId,
    SessionId,
    SessionTopic,
    TagId,
    TopicId,
)
from sqlalchemy import ARRAY, Boolean, Double, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator, TypeEngine, UserDefinedType

type _Impl = TypeEngine[Any] | type[TypeEngine[Any]]  # pyright: ignore[reportExplicitAny]


class SessionIdType(TypeDecorator[SessionId]):
    impl: _Impl = PGUUID(as_uuid=True)
    cache_ok: bool | None = True

    @override
    def process_bind_param(self, value: SessionId | None, dialect: Dialect) -> object:
        return value.value if value is not None else None

    @override
    def process_result_value(self, value: object, dialect: Dialect) -> SessionId | None:
        return SessionId(value=value) if value is not None else None  # pyright: ignore[reportArgumentType]


class MessageIdType(TypeDecorator[MessageId]):
    impl: _Impl = PGUUID(as_uuid=True)
    cache_ok: bool | None = True

    @override
    def process_bind_param(self, value: MessageId | None, dialect: Dialect) -> object:
        return value.value if value is not None else None

    @override
    def process_result_value(self, value: object, dialect: Dialect) -> MessageId | None:
        return MessageId(value=value) if value is not None else None  # pyright: ignore[reportArgumentType]


class NoteIdType(TypeDecorator[NoteId]):
    impl: _Impl = PGUUID(as_uuid=True)
    cache_ok: bool | None = True

    @override
    def process_bind_param(self, value: NoteId | None, dialect: Dialect) -> object:
        return value.value if value is not None else None

    @override
    def process_result_value(self, value: object, dialect: Dialect) -> NoteId | None:
        return NoteId(value=value) if value is not None else None  # pyright: ignore[reportArgumentType]


class TopicIdType(TypeDecorator[TopicId]):
    impl: _Impl = PGUUID(as_uuid=True)
    cache_ok: bool | None = True

    @override
    def process_bind_param(self, value: TopicId | None, dialect: Dialect) -> object:
        return value.value if value is not None else None

    @override
    def process_result_value(self, value: object, dialect: Dialect) -> TopicId | None:
        return TopicId(value=value) if value is not None else None  # pyright: ignore[reportArgumentType]


class TagIdType(TypeDecorator[TagId]):
    impl: _Impl = PGUUID(as_uuid=True)
    cache_ok: bool | None = True

    @override
    def process_bind_param(self, value: TagId | None, dialect: Dialect) -> object:
        return value.value if value is not None else None

    @override
    def process_result_value(self, value: object, dialect: Dialect) -> TagId | None:
        return TagId(value=value) if value is not None else None  # pyright: ignore[reportArgumentType]


class SessionTopicType(TypeDecorator[SessionTopic]):
    impl: _Impl = String
    cache_ok: bool | None = True

    @override
    def process_bind_param(
        self, value: SessionTopic | None, dialect: Dialect
    ) -> object:
        return value.value if value is not None else None

    @override
    def process_result_value(
        self, value: object, dialect: Dialect
    ) -> SessionTopic | None:
        return SessionTopic(value=value) if value is not None else None  # pyright: ignore[reportArgumentType]


class LabelType(TypeDecorator[Label]):
    impl: _Impl = String
    cache_ok: bool | None = True

    @override
    def process_bind_param(self, value: Label | None, dialect: Dialect) -> object:
        return value.value if value is not None else None

    @override
    def process_result_value(self, value: object, dialect: Dialect) -> Label | None:
        return Label(value=value) if value is not None else None  # pyright: ignore[reportArgumentType]


class MessageContentType(TypeDecorator[MessageContent]):
    impl: _Impl = Text
    cache_ok: bool | None = True

    @override
    def process_bind_param(
        self, value: MessageContent | None, dialect: Dialect
    ) -> object:
        return value.value if value is not None else None

    @override
    def process_result_value(
        self, value: object, dialect: Dialect
    ) -> MessageContent | None:
        return MessageContent(value=value) if value is not None else None  # pyright: ignore[reportArgumentType]


class NoteContentType(TypeDecorator[NoteContent]):
    impl: _Impl = Text
    cache_ok: bool | None = True

    @override
    def process_bind_param(self, value: NoteContent | None, dialect: Dialect) -> object:
        return value.value if value is not None else None

    @override
    def process_result_value(
        self, value: object, dialect: Dialect
    ) -> NoteContent | None:
        return NoteContent(value=value) if value is not None else None  # pyright: ignore[reportArgumentType]


class CoverageHistoryType(TypeDecorator[tuple[Coverage, ...]]):
    impl: _Impl = ARRAY(Double[float]())
    cache_ok: bool | None = True

    @override
    def process_bind_param(
        self, value: tuple[Coverage, ...] | None, dialect: Dialect
    ) -> object:
        return [coverage.value for coverage in value] if value is not None else None

    @override
    def process_result_value(
        self, value: object, dialect: Dialect
    ) -> tuple[Coverage, ...] | None:
        if value is None:
            return None
        components = cast(list[float], value)
        return tuple(Coverage(value=component) for component in components)


class DraftingConsentType(TypeDecorator[DraftingConsent | None]):
    impl: _Impl = Boolean
    cache_ok: bool | None = True

    @override
    def process_bind_param(
        self, value: DraftingConsent | None, dialect: Dialect
    ) -> object:
        return value is not None

    @override
    def process_result_value(
        self, value: object, dialect: Dialect
    ) -> DraftingConsent | None:
        return DraftingConsent() if value else None


class ConversationRequestType(TypeDecorator[ConversationRequest | None]):
    impl: _Impl = Boolean
    cache_ok: bool | None = True

    @override
    def process_bind_param(
        self, value: ConversationRequest | None, dialect: Dialect
    ) -> object:
        return value is not None

    @override
    def process_result_value(
        self, value: object, dialect: Dialect
    ) -> ConversationRequest | None:
        return ConversationRequest() if value else None


class VectorType(UserDefinedType[tuple[float, ...]]):
    cache_ok: bool | None = True

    @override
    def get_col_spec(self, **kw: object) -> str:
        return "vector"

    @override
    def bind_processor(self, dialect: Dialect):
        def process(value: tuple[float, ...] | None) -> str | None:
            if value is None:
                return None
            return "[" + ",".join(repr(component) for component in value) + "]"

        return process

    @override
    def result_processor(self, dialect: Dialect, coltype: object):
        def process(value: object) -> tuple[float, ...] | None:
            if value is None:
                return None
            text = cast(str, value).strip("[]")
            if not text:
                return ()
            return tuple(float(component) for component in text.split(","))

        return process
