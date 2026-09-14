from domain.remember.sitting import Sitting
from domain.remember.value_objects import SittingId
from domain.shared.identity.model import UserId


class InMemorySittingRepository:
    def __init__(self) -> None:
        self._sittings: dict[SittingId, Sitting] = {}

    async def save(self, sitting: Sitting) -> None:
        self._sittings[sitting.id] = sitting

    async def get(self, sitting_id: SittingId) -> Sitting | None:
        return self._sittings.get(sitting_id)

    async def latest(self, owner: UserId) -> Sitting | None:
        owned = [
            sitting for sitting in self._sittings.values() if sitting.owner_id == owner
        ]
        if not owned:
            return None
        return max(owned, key=lambda sitting: sitting.opened_at)

    def snapshot(self) -> dict[SittingId, Sitting]:
        return dict(self._sittings)

    def restore(self, snapshot: dict[SittingId, Sitting]) -> None:
        self._sittings = dict(snapshot)
