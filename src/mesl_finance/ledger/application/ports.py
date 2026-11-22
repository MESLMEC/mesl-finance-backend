from typing import Protocol

from mesl_finance.ledger.domain.deposit import Deposit
from mesl_finance.ledger.domain.entry import EntryKind
from mesl_finance.ledger.domain.entry_list import EntryView, ListEntriesQuery
from mesl_finance.ledger.domain.expense import Expense
from mesl_finance.ledger.domain.fix_amount import AmountFix
from mesl_finance.ledger.domain.label_edit import LabelEdit, LabelView
from mesl_finance.ledger.domain.refund import Refund
from mesl_finance.ledger.domain.transfer import Transfer
from mesl_finance.shared.idempotency import IdempotencyStore
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

    @property
    def idempotency(self) -> IdempotencyStore:
        """The key store, sharing this transaction (issue #4)."""
        ...


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


class TransferRepository(Protocol):
    """What the transfer action needs (D-085: a slice declares its own port)."""

    async def open_tenure_id(self) -> int:
        """The id of the open tenure, or raise NoOpenTenure."""
        ...

    async def add_transfer(
        self, tenure_id: int, transfer: Transfer, recorded_by: str
    ) -> tuple[int, int, int]:
        """Write the header + two zero-summing lines; returns (id, from, to balances)."""
        ...


class TransferUnitOfWork(UnitOfWork, Protocol):
    """The transfer action's transaction scope."""

    @property
    def ledger(self) -> TransferRepository: ...


class FixAmountRepository(Protocol):
    """What the fix-amount action needs; the deposit slice keeps its own port."""

    async def open_tenure_id(self) -> int:
        """The id of the open tenure, or raise NoOpenTenure."""
        ...

    async def fix_amount(
        self, tenure_id: int, fix: AmountFix, recorded_by: str
    ) -> tuple[int, int, EntryKind, int]:
        """Write the reversal mirror and the replacement (header + lines) in the
        ONE transaction; returns (replacement_id, reversal_id, kind, balance)."""
        ...


class FixAmountUnitOfWork(UnitOfWork, Protocol):
    """The fix-amount action's transaction scope."""

    @property
    def ledger(self) -> FixAmountRepository: ...


class LabelEditRepository(Protocol):
    """What the label-edit action needs; the other slices keep their own ports."""

    async def edit_labels(self, edit: LabelEdit) -> LabelView:
        """Write the edit in one UPDATE; returns the entry's labels after the write."""
        ...


class LabelEditUnitOfWork(UnitOfWork, Protocol):
    """The label-edit action's transaction scope."""

    @property
    def ledger(self) -> LabelEditRepository: ...


class EntryListRepository(Protocol):
    """What the entry-list read needs; the write slices keep their own ports."""

    async def list_entries(self, query: ListEntriesQuery) -> list[EntryView]:
        """The ``entries_current`` rows, newest id last (optionally one tenure)."""
        ...


class EntryListUnitOfWork(UnitOfWork, Protocol):
    """The entry-list read's transaction scope."""

    @property
    def ledger(self) -> EntryListRepository: ...


class RefundRepository(Protocol):
    """What the refund action needs; the other slices keep their own ports."""

    async def open_tenure_id(self) -> int:
        """The id of the open tenure, or raise NoOpenTenure."""
        ...

    async def add_refund(self, tenure_id: int, refund: Refund, recorded_by: str) -> tuple[int, int]:
        """Write the member-linked expense out of the pool; (id, pool balance)."""
        ...


class RefundUnitOfWork(UnitOfWork, Protocol):
    """The refund action's transaction scope."""

    @property
    def ledger(self) -> RefundRepository: ...
