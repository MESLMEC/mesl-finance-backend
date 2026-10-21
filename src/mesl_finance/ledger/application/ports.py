from typing import Protocol

from mesl_finance.ledger.domain.deposit import Deposit
from mesl_finance.ledger.domain.expense import Expense
from mesl_finance.shared.ports import UnitOfWork


class LedgerRepository(Protocol):
    async def open_tenure_id(self) -> int:
        """The id of the open tenure, or raise NoOpenTenure."""
        ...

    async def add_deposit(self, tenure_id: int, deposit: Deposit, recorded_by: str) -> int:
        """Write the entry (header + line); returns the new entry id."""
        ...


class LedgerUnitOfWork(UnitOfWork, Protocol):
    """The ledger's transaction scope: the shared scope plus its repository."""

    @property
    def ledger(self) -> LedgerRepository: ...


class ExpenseRepository(Protocol):
    """What the expense action needs; the deposit slice keeps its own port."""

    async def open_tenure_id(self) -> int:
        """The id of the open tenure, or raise NoOpenTenure."""
        ...

    async def add_expense(
        self, tenure_id: int, expense: Expense, recorded_by: str
    ) -> tuple[int, int]:
        """Write the entry (header + one negative line); returns (id, balance after)."""
        ...


class ExpenseUnitOfWork(UnitOfWork, Protocol):
    """The expense action's transaction scope."""

    @property
    def ledger(self) -> ExpenseRepository: ...
