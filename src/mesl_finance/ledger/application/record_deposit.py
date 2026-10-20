from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from mesl_finance.ledger.application.ports import LedgerUnitOfWork
from mesl_finance.ledger.domain.deposit import Deposit, DepositSource


@dataclass(frozen=True)
class RecordDepositCommand:
    amount: int
    occurred_on: date
    source: DepositSource
    note: str = ""
    tag: str | None = None
    cost_center_id: int | None = None
    member_id: int | None = None
    envelope_id: int | None = None


class RecordDeposit:
    """Business action: record money coming in, in ONE transaction."""

    def __init__(self, unit_of_work: Callable[[str], LedgerUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, command: RecordDepositCommand, actor: str) -> int:
        deposit = Deposit.create(
            amount=command.amount,
            occurred_on=command.occurred_on,
            source=command.source,
            note=command.note,
            tag=command.tag,
            cost_center_id=command.cost_center_id,
            member_id=command.member_id,
            envelope_id=command.envelope_id,
        )
        async with self._unit_of_work(actor) as uow:
            tenure_id = await uow.ledger.open_tenure_id()
            entry_id = await uow.ledger.add_deposit(tenure_id, deposit, recorded_by=actor)
            await uow.commit()
        return entry_id
