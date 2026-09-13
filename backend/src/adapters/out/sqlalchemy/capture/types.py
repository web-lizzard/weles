from enum import StrEnum
from typing import Any, override

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
        raise NotImplementedError

    @override
    def process_result_value(self, value: object, dialect: Dialect) -> SessionId | None:
        raise NotImplementedError


class MessageIdType(TypeDecorator[MessageId]):
    impl: _Impl = PGUUID(as_uuid=True)
    cache_ok: bool | None = True

    @override
    def process_bind_param(self, value: MessageId | None, dialect: Dialect) -> object:
        raise NotImplementedError

    @override
    def process_result_value(self, value: object, dialect: Dialect) -> MessageId | None:
        raise NotImplementedError


class NoteIdType(TypeDecorator[NoteId]):
    impl: _Impl = PGUUID(as_uuid=True)
    cache_ok: bool | None = True

    @override
    def process_bind_param(self, value: NoteId | None, dialect: Dialect) -> object:
        raise NotImplementedError

    @override
    def process_result_value(self, value: object, dialect: Dialect) -> NoteId | None:
        raise NotImplementedError


class TopicIdType(TypeDecorator[TopicId]):
    impl: _Impl = PGUUID(as_uuid=True)
    cache_ok: bool | None = True

    @override
    def process_bind_param(self, value: TopicId | None, dialect: Dialect) -> object:
        raise NotImplementedError

    @override
    def process_result_value(self, value: object, dialect: Dialect) -> TopicId | None:
        raise NotImplementedError


class TagIdType(TypeDecorator[TagId]):
    impl: _Impl = PGUUID(as_uuid=True)
    cache_ok: bool | None = True

    @override
    def process_bind_param(self, value: TagId | None, dialect: Dialect) -> object:
        raise NotImplementedError

    @override
    def process_result_value(self, value: object, dialect: Dialect) -> TagId | None:
        raise NotImplementedError


class SessionTopicType(TypeDecorator[SessionTopic]):
    impl: _Impl = String
    cache_ok: bool | None = True

    @override
    def process_bind_param(
        self, value: SessionTopic | None, dialect: Dialect
    ) -> object:
        raise NotImplementedError

    @override
    def process_result_value(
        self, value: object, dialect: Dialect
    ) -> SessionTopic | None:
        raise NotImplementedError


class LabelType(TypeDecorator[Label]):
    impl: _Impl = String
    cache_ok: bool | None = True

    @override
    def process_bind_param(self, value: Label | None, dialect: Dialect) -> object:
        raise NotImplementedError

    @override
    def process_result_value(self, value: object, dialect: Dialect) -> Label | None:
        raise NotImplementedError


class MessageContentType(TypeDecorator[MessageContent]):
    impl: _Impl = Text
    cache_ok: bool | None = True

    @override
    def process_bind_param(
        self, value: MessageContent | None, dialect: Dialect
    ) -> object:
        raise NotImplementedError

    @override
    def process_result_value(
        self, value: object, dialect: Dialect
    ) -> MessageContent | None:
        raise NotImplementedError


class NoteContentType(TypeDecorator[NoteContent]):
    impl: _Impl = Text
    cache_ok: bool | None = True

    @override
    def process_bind_param(self, value: NoteContent | None, dialect: Dialect) -> object:
        raise NotImplementedError

    @override
    def process_result_value(
        self, value: object, dialect: Dialect
    ) -> NoteContent | None:
        raise NotImplementedError


class StrEnumType[EnumT: StrEnum](TypeDecorator[EnumT]):
    impl: _Impl = String
    cache_ok: bool | None = True

    def __init__(self, enum_cls: type[EnumT]) -> None:
        super().__init__()
        self._enum_cls: type[EnumT] = enum_cls

    @override
    def process_bind_param(self, value: EnumT | None, dialect: Dialect) -> object:
        raise NotImplementedError

    @override
    def process_result_value(self, value: object, dialect: Dialect) -> EnumT | None:
        raise NotImplementedError


class CoverageHistoryType(TypeDecorator[tuple[Coverage, ...]]):
    impl: _Impl = ARRAY(Double[float]())
    cache_ok: bool | None = True

    @override
    def process_bind_param(
        self, value: tuple[Coverage, ...] | None, dialect: Dialect
    ) -> object:
        raise NotImplementedError

    @override
    def process_result_value(
        self, value: object, dialect: Dialect
    ) -> tuple[Coverage, ...] | None:
        raise NotImplementedError


class DraftingConsentType(TypeDecorator[DraftingConsent | None]):
    impl: _Impl = Boolean
    cache_ok: bool | None = True

    @override
    def process_bind_param(
        self, value: DraftingConsent | None, dialect: Dialect
    ) -> object:
        raise NotImplementedError

    @override
    def process_result_value(
        self, value: object, dialect: Dialect
    ) -> DraftingConsent | None:
        raise NotImplementedError


class ConversationRequestType(TypeDecorator[ConversationRequest | None]):
    impl: _Impl = Boolean
    cache_ok: bool | None = True

    @override
    def process_bind_param(
        self, value: ConversationRequest | None, dialect: Dialect
    ) -> object:
        raise NotImplementedError

    @override
    def process_result_value(
        self, value: object, dialect: Dialect
    ) -> ConversationRequest | None:
        raise NotImplementedError


class VectorType(UserDefinedType[tuple[float, ...]]):
    cache_ok: bool | None = True

    @override
    def get_col_spec(self, **kw: object) -> str:
        return "vector"

    @override
    def bind_processor(self, dialect: Dialect):
        def process(value: tuple[float, ...] | None) -> str | None:
            _ = value
            raise NotImplementedError

        return process

    @override
    def result_processor(self, dialect: Dialect, coltype: object):
        def process(value: object) -> tuple[float, ...] | None:
            _ = value
            raise NotImplementedError

        return process
