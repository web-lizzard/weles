import re
from typing import ClassVar


class CoreException(Exception):
    _code: ClassVar[str]

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if "_code" not in cls.__dict__:
            cls._code = _to_snake_case(cls.__name__)

    @classmethod
    def code(cls) -> str:
        return cls._code


_TRAILING_SUFFIXES = ("Error", "Exception")


def _to_snake_case(name: str) -> str:
    for suffix in _TRAILING_SUFFIXES:
        if name.endswith(suffix) and name != suffix:
            name = name[: -len(suffix)]
            break
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
