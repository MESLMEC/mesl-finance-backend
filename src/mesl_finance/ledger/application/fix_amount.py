from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from mesl_finance.ledger.application.ports import FixAmountUnitOfWork
from mesl_finance.ledger.domain.entry import EntryKind
from mesl_finance.ledger.domain.fix_amount import AmountFix


@dataclass(frozen=True)
class FixAmountCommand:
    entry_id: int
    amount: int
    occurred_on: date
    note: str


class FixAmount:
    """Business action: fix an entry's amount as a reversal plus a replacement,
    both written in ONE transaction."""

    def __init__(self, unit_of_work: Callable[[str], FixAmountUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(
        self, command: FixAmountCommand, actor: str
    ) -> tuple[int, int, EntryKind, int]:
        """Returns (replacement_id, reversal_id, kind, balance after the write)."""
        fix = AmountFix.create(
            entry_id=command.entry_id,
            amount=command.amount,
            occurred_on=command.occurred_on,
            note=command.note,
        )
        async with self._unit_of_work(actor) as uow:
            tenure_id = await uow.ledger.open_tenure_id()
            replacement_id, reversal_id, kind, balance = await uow.ledger.fix_amount(
                tenure_id, fix, recorded_by=actor
            )
            await uow.commit()
        return replacement_id, reversal_id, kind, balance
