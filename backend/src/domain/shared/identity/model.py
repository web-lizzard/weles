from uuid import UUID, uuid4

from pydantic import BaseModel


class UserId(BaseModel, frozen=True):
    """The only thing about a person the core ever sees.

    Shared by every bounded context, and the key S-04 and S-05 attach data to.
    The core never mints one for a real person: the auth adapter does, at
    registration, and hands it inward as an explicit input. There is no ambient
    "current user" reader anywhere in the core.

    In S-01 no handler receives it yet; the sign-in gate produces it and routes
    drop it.
    """

    value: UUID

    @classmethod
    def new(cls) -> "UserId":
        return cls(value=uuid4())
