from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from mesl_finance.ledger.application.ports import ExpenseUnitOfWork
from mesl_finance.ledger.domain.expense import Expense


@dataclass(frozen=True)
class RecordExpenseCommand:
    amount: int
    occurred_on: date
    envelope_id: int
    note: str = ""
    tag: str | None = None
    cost_center_id: int | None = None


class RecordExpense:
    """Business action: record money going out, in ONE transaction."""

    def __init__(self, unit_of_work: Callable[[str], ExpenseUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, command: RecordExpenseCommand, actor: str) -> tuple[int, int]:
        expense = Expense.create(
            amount=command.amount,
            occurred_on=command.occurred_on,
            envelope_id=command.envelope_id,
            note=command.note,
            tag=command.tag,
            cost_center_id=command.cost_center_id,
        )
        async with self._unit_of_work(actor) as uow:
            tenure_id = await uow.ledger.open_tenure_id()
            entry_id, balance = await uow.ledger.add_expense(tenure_id, expense, recorded_by=actor)
            await uow.commit()
        return entry_id, balance
