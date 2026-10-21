from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from mesl_finance.ledger.application.ports import TransferUnitOfWork
from mesl_finance.ledger.domain.transfer import Transfer


@dataclass(frozen=True)
class RecordTransferCommand:
    amount: int
    occurred_on: date
    from_envelope_id: int
    to_envelope_id: int
    note: str
    tag: str | None = None
    cost_center_id: int | None = None


class RecordTransfer:
    """Business action: move money between two envelopes, in ONE transaction."""

    def __init__(self, unit_of_work: Callable[[str], TransferUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, command: RecordTransferCommand, actor: str) -> tuple[int, int, int]:
        transfer = Transfer.create(
            amount=command.amount,
            occurred_on=command.occurred_on,
            from_envelope_id=command.from_envelope_id,
            to_envelope_id=command.to_envelope_id,
            note=command.note,
            tag=command.tag,
            cost_center_id=command.cost_center_id,
        )
        async with self._unit_of_work(actor) as uow:
            tenure_id = await uow.ledger.open_tenure_id()
            entry_id, from_balance, to_balance = await uow.ledger.add_transfer(
                tenure_id, transfer, recorded_by=actor
            )
            await uow.commit()
        return entry_id, from_balance, to_balance
