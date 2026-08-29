from typing import ClassVar


class CoreException(Exception):
    _code: ClassVar[str]

    @classmethod
    def code(cls) -> str:
        raise NotImplementedError
