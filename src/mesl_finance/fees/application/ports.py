from typing import Protocol

from mesl_finance.fees.domain.dues import StandingView
from mesl_finance.fees.domain.fee_rate import FeeRate, FeeRateView
from mesl_finance.fees.domain.shutdown import ShutdownEventView, ShutdownWeeks
from mesl_finance.shared.ports import UnitOfWork


class FeeRepository(Protocol):
    async def add_rate(self, rate: FeeRate, recorded_by: str) -> FeeRateView:
        """Write a new rate; returns the stored row."""
        ...

    async def list_rates(self) -> list[FeeRateView]:
        """Every rate, in effective_from and id order."""
        ...

    async def set_shutdown(self, shutdown: ShutdownWeeks, recorded_by: str) -> int:
        """Mark or reopen each named week; returns the number of rows written."""
        ...

    async def list_shutdown_events(self) -> list[ShutdownEventView]:
        """Every shutdown event, in week_start and id order."""
        ...


class FeeUnitOfWork(UnitOfWork, Protocol):
    """The fees' transaction scope: the shared scope plus its repository."""

    @property
    def fees(self) -> FeeRepository: ...


class DuesRepository(Protocol):
    """What the dues read needs; the write slices keep their own port."""

    async def list_dues(self) -> list[StandingView]:
        """Every ``dues_overview`` row, in the view's order."""
        ...


class DuesUnitOfWork(UnitOfWork, Protocol):
    """The dues read's transaction scope."""

    @property
    def dues(self) -> DuesRepository: ...
