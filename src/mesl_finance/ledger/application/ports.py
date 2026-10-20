from types import TracebackType
from typing import Protocol

from mesl_finance.ledger.domain.deposit import Deposit


class LedgerRepository(Protocol):
    async def open_tenure_id(self) -> int:
        """The id of the open tenure, or raise NoOpenTenure."""
        ...

    async def add_deposit(self, tenure_id: int, deposit: Deposit, recorded_by: str) -> int:
        """Write the entry (header + line); returns the new entry id."""
        ...


class LedgerUnitOfWork(Protocol):
    @property
    def ledger(self) -> LedgerRepository: ...

    async def __aenter__(self) -> "LedgerUnitOfWork": ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...
