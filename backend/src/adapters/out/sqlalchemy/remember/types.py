# pyright: reportUnusedParameter=false
from typing import Any, override

from domain.remember.value_objects import (
    CardId,
    OpaqueSchedulerState,
    ResumeHorizon,
    ShowingLimit,
    SittingId,
)
from sqlalchemy import Integer, Interval
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator, TypeEngine

type _Impl = TypeEngine[Any] | type[TypeEngine[Any]]  # pyright: ignore[reportExplicitAny]


class SittingIdType(TypeDecorator[SittingId]):
    impl: _Impl = PGUUID(as_uuid=True)
    cache_ok: bool | None = True

    @override
    def process_bind_param(self, value: SittingId | None, dialect: Dialect) -> object:
        raise NotImplementedError

    @override
    def process_result_value(self, value: object, dialect: Dialect) -> SittingId | None:
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


class ShowingLimitType(TypeDecorator[ShowingLimit]):
    impl: _Impl = Integer
    cache_ok: bool | None = True

    @override
    def process_bind_param(
        self, value: ShowingLimit | None, dialect: Dialect
    ) -> object:
        raise NotImplementedError

    @override
    def process_result_value(
        self, value: object, dialect: Dialect
    ) -> ShowingLimit | None:
        raise NotImplementedError


class ResumeHorizonType(TypeDecorator[ResumeHorizon]):
    impl: _Impl = Interval
    cache_ok: bool | None = True

    @override
    def process_bind_param(
        self, value: ResumeHorizon | None, dialect: Dialect
    ) -> object:
        raise NotImplementedError

    @override
    def process_result_value(
        self, value: object, dialect: Dialect
    ) -> ResumeHorizon | None:
        raise NotImplementedError


class OpaqueSchedulerStateType(TypeDecorator[OpaqueSchedulerState]):
    impl: _Impl = JSONB
    cache_ok: bool | None = True

    @override
    def process_bind_param(
        self, value: OpaqueSchedulerState | None, dialect: Dialect
    ) -> object:
        raise NotImplementedError

    @override
    def process_result_value(
        self, value: object, dialect: Dialect
    ) -> OpaqueSchedulerState | None:
        raise NotImplementedError
