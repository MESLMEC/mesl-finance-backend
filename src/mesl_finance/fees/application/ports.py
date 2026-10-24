from typing import Protocol

from mesl_finance.fees.domain.fee_rate import FeeRate, FeeRateView
from mesl_finance.fees.domain.shutdown import ShutdownEventView, ShutdownRange
from mesl_finance.shared.ports import UnitOfWork


class FeeRepository(Protocol):
    async def add_rate(self, rate: FeeRate, recorded_by: str) -> FeeRateView:
        """Write a new rate; returns the stored row."""
        ...

    async def list_rates(self) -> list[FeeRateView]:
        """Every rate, in effective_from and id order."""
        ...

    async def set_shutdown(self, shutdown: ShutdownRange, recorded_by: str) -> int:
        """Mark or reopen the whole range; returns the number of weeks written."""
        ...

    async def list_shutdown_events(self) -> list[ShutdownEventView]:
        """Every shutdown event, in week_start and id order."""
        ...


class FeeUnitOfWork(UnitOfWork, Protocol):
    """The fees' transaction scope: the shared scope plus its repository."""

    @property
    def fees(self) -> FeeRepository: ...
