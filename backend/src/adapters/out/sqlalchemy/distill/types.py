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
        return value.value if value is not None else None

    @override
    def process_result_value(self, value: object, dialect: Dialect) -> NoteId | None:
        return NoteId(value=value) if value is not None else None  # pyright: ignore[reportArgumentType]


class SessionIdType(TypeDecorator[SessionId]):
    impl: _Impl = PGUUID(as_uuid=True)
    cache_ok: bool | None = True

    @override
    def process_bind_param(self, value: SessionId | None, dialect: Dialect) -> object:
        return value.value if value is not None else None

    @override
    def process_result_value(self, value: object, dialect: Dialect) -> SessionId | None:
        return SessionId(value=value) if value is not None else None  # pyright: ignore[reportArgumentType]


class CardIdType(TypeDecorator[CardId]):
    impl: _Impl = PGUUID(as_uuid=True)
    cache_ok: bool | None = True

    @override
    def process_bind_param(self, value: CardId | None, dialect: Dialect) -> object:
        return value.value if value is not None else None

    @override
    def process_result_value(self, value: object, dialect: Dialect) -> CardId | None:
        return CardId(value=value) if value is not None else None  # pyright: ignore[reportArgumentType]


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


class CardSideType(TypeDecorator[CardSide]):
    impl: _Impl = Text
    cache_ok: bool | None = True

    @override
    def process_bind_param(self, value: CardSide | None, dialect: Dialect) -> object:
        return value.value if value is not None else None

    @override
    def process_result_value(self, value: object, dialect: Dialect) -> CardSide | None:
        return CardSide(value=value) if value is not None else None  # pyright: ignore[reportArgumentType]


class AnchorType(TypeDecorator[Anchor]):
    impl: _Impl = Text
    cache_ok: bool | None = True

    @override
    def process_bind_param(self, value: Anchor | None, dialect: Dialect) -> object:
        return value.quote if value is not None else None

    @override
    def process_result_value(self, value: object, dialect: Dialect) -> Anchor | None:
        return Anchor(quote=value) if value is not None else None  # pyright: ignore[reportArgumentType]
