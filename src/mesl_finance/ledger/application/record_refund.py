from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from mesl_finance.ledger.application.ports import RefundUnitOfWork
from mesl_finance.ledger.domain.refund import Refund


@dataclass(frozen=True)
class RecordRefundCommand:
    member_id: int
    amount: int
    occurred_on: date
    note: str = ""
    tag: str | None = None
    cost_center_id: int | None = None


class RecordRefund:
    """Business action: refund a member out of the pool, in ONE transaction."""

    def __init__(self, unit_of_work: Callable[[str], RefundUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, command: RecordRefundCommand, actor: str) -> tuple[int, int]:
        refund = Refund.create(
            member_id=command.member_id,
            amount=command.amount,
            occurred_on=command.occurred_on,
            note=command.note,
            tag=command.tag,
            cost_center_id=command.cost_center_id,
        )
        async with self._unit_of_work(actor) as uow:
            tenure_id = await uow.ledger.open_tenure_id()
            entry_id, balance = await uow.ledger.add_refund(tenure_id, refund, recorded_by=actor)
            await uow.commit()
        return entry_id, balance
