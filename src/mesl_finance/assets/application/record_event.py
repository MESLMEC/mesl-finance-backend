from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from mesl_finance.assets.application.ports import AssetUnitOfWork
from mesl_finance.assets.domain.asset_event import AssetEvent, AssetEventView


@dataclass(frozen=True)
class RecordEventCommand:
    asset_id: int
    kind: str
    quantity: int
    occurred_on: date
    member_id: int | None = None
    source: str | None = None
    ledger_transaction_id: int | None = None
    note: str = ""


class RecordAssetEvent:
    """Business action: record one asset event, in ONE transaction.

    The kind shapes (quantity sign, `source`/`member_id` pairing, required
    note) are validated by the ROUTER through `AssetEvent.create` before this
    use case runs (approved option a, D-090's pattern: the kind-dependent
    rules are not the use case's business). Here the command's fields are
    passed through unchanged.
    """

    def __init__(self, unit_of_work: Callable[[str], AssetUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, command: RecordEventCommand, actor: str) -> AssetEventView | None:
        event = AssetEvent(
            kind=command.kind,
            quantity=command.quantity,
            occurred_on=command.occurred_on,
            member_id=command.member_id,
            source=command.source,
            ledger_transaction_id=command.ledger_transaction_id,
            note=command.note,
        )
        async with self._unit_of_work(actor) as uow:
            event_id = await uow.assets.add_event(command.asset_id, event, actor)
            if event_id is None:
                return None
            await uow.commit()
        return AssetEventView(
            id=event_id,
            asset_id=command.asset_id,
            kind=event.kind,
            quantity=event.quantity,
            occurred_on=event.occurred_on,
            note=event.note,
            ledger_transaction_id=event.ledger_transaction_id,
        )
