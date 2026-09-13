from enum import StrEnum
from typing import Any, override

from sqlalchemy import String
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator, TypeEngine

type _Impl = TypeEngine[Any] | type[TypeEngine[Any]]  # pyright: ignore[reportExplicitAny]


class StrEnumType[EnumT: StrEnum](TypeDecorator[EnumT]):
    impl: _Impl = String
    cache_ok: bool | None = True

    def __init__(self, enum_cls: type[EnumT]) -> None:
        super().__init__()
        self._enum_cls: type[EnumT] = enum_cls

    @override
    def process_bind_param(self, value: EnumT | None, dialect: Dialect) -> object:
        return value.value if value is not None else None

    @override
    def process_result_value(self, value: object, dialect: Dialect) -> EnumT | None:
        return self._enum_cls(value) if value is not None else None
