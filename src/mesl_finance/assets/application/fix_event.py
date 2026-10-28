from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from mesl_finance.assets.application.ports import FixEventUnitOfWork
from mesl_finance.assets.domain.asset_event import AssetEventView
from mesl_finance.assets.domain.asset_event_fix import AssetEventFix


@dataclass(frozen=True)
class FixEventCommand:
    asset_id: int
    event_id: int
    quantity: int
    occurred_on: date
    note: str


class FixAssetEvent:
    """Business action: fix an asset event as a mirroring reversal plus a
    replacement, both written in ONE transaction.

    The kind shapes are not this use case's business (the 9.1 pattern): the
    domain refusal fires before any transaction opens, the adapter writes the
    two rows, and PostgreSQL owns the mirror, tenure and bucket walls.
    """

    def __init__(self, unit_of_work: Callable[[str], FixEventUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(
        self, command: FixEventCommand, actor: str
    ) -> tuple[AssetEventView, int] | None:
        """Returns (replacement view, reversal id); None when the asset or the
        event does not exist (the router then answers 404)."""
        fix = AssetEventFix.create(
            event_id=command.event_id,
            quantity=command.quantity,
            occurred_on=command.occurred_on,
            note=command.note,
        )
        async with self._unit_of_work(actor) as uow:
            answer = await uow.fix_events.fix_event(
                command.asset_id, command.event_id, fix, recorded_by=actor
            )
            if answer is None:
                return None
            _replacement_id, reversal_id, view = answer
            await uow.commit()
        return view, reversal_id
