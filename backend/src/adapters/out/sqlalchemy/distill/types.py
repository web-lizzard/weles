from typing import Any, override

from domain.distill.value_objects import (
    Anchor,
    CardId,
    CardSide,
    NoteContent,
    NoteId,
    SessionId,
)
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator, TypeEngine

type _Impl = TypeEngine[Any] | type[TypeEngine[Any]]  # pyright: ignore[reportExplicitAny]


class NoteIdType(TypeDecorator[NoteId]):
    impl: _Impl = PGUUID(as_uuid=True)
    cache_ok: bool | None = True

    @override
    def process_bind_param(self, value: NoteId | None, dialect: Dialect) -> object:
        raise NotImplementedError

    @override
    def process_result_value(self, value: object, dialect: Dialect) -> NoteId | None:
        raise NotImplementedError


class SessionIdType(TypeDecorator[SessionId]):
    impl: _Impl = PGUUID(as_uuid=True)
    cache_ok: bool | None = True

    @override
    def process_bind_param(self, value: SessionId | None, dialect: Dialect) -> object:
        raise NotImplementedError

    @override
    def process_result_value(self, value: object, dialect: Dialect) -> SessionId | None:
        raise NotImplementedError


class CardIdType(TypeDecorator[CardId]):
    impl: _Impl = PGUUID(as_uuid=True)
    cache_ok: bool | None = True

    @override
    def process_bind_param(self, value: CardId | None, dialect: Dialect) -> object:
        raise NotImplementedError

    @override
    def process_result_value(self, value: object, dialect: Dialect) -> CardId | None:
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


class CardSideType(TypeDecorator[CardSide]):
    impl: _Impl = Text
    cache_ok: bool | None = True

    @override
    def process_bind_param(self, value: CardSide | None, dialect: Dialect) -> object:
        raise NotImplementedError

    @override
    def process_result_value(self, value: object, dialect: Dialect) -> CardSide | None:
        raise NotImplementedError


class AnchorType(TypeDecorator[Anchor]):
    impl: _Impl = Text
    cache_ok: bool | None = True

    @override
    def process_bind_param(self, value: Anchor | None, dialect: Dialect) -> object:
        raise NotImplementedError

    @override
    def process_result_value(self, value: object, dialect: Dialect) -> Anchor | None:
        raise NotImplementedError
