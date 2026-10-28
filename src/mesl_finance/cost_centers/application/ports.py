from typing import Protocol

from mesl_finance.cost_centers.domain.cost_center import CostCenter, CostCenterView
from mesl_finance.cost_centers.domain.cost_center_summary import CostCenterSummary
from mesl_finance.cost_centers.domain.sweep import Sweep
from mesl_finance.shared.ports import UnitOfWork


class CostCenterRepository(Protocol):
    async def list_all(self, kind: str | None, status: str | None) -> list[CostCenterView]:
        """Every cost center (optionally filtered), in id order."""
        ...

    async def add(self, cost_center: CostCenter) -> CostCenterView:
        """Write a new cost center; returns the stored row."""
        ...

    async def rename(self, cost_center_id: int, name: str) -> CostCenterView | None:
        """Rename one cost center; None when the id does not exist."""
        ...

    async def set_status(self, cost_center_id: int, status: str) -> CostCenterView | None:
        """Replace one cost center's status; None when the id does not exist."""
        ...


class CostCenterUnitOfWork(UnitOfWork, Protocol):
    """The cost centers' transaction scope: the shared scope plus its repository."""

    @property
    def cost_centers(self) -> CostCenterRepository: ...


class SweepRepository(Protocol):
    """What the sweep action needs; each write slice keeps its own port (D-085)."""

    async def open_tenure_id(self) -> int:
        """The open tenure's id, so a missing one answers ``no_open_tenure``."""
        ...

    async def sweep(self, sweep: Sweep, recorded_by: str) -> tuple[int, int, int]:
        """Call ``sweep_leftover``; returns (entry id, from balance, pool balance)."""
        ...


class SweepUnitOfWork(UnitOfWork, Protocol):
    """The sweep's transaction scope."""

    @property
    def sweeps(self) -> SweepRepository: ...


class CostCenterSummaryRepository(Protocol):
    """What the event-leftover read needs; the write slices keep their own port."""

    async def get_summary(self, cost_center_id: int) -> CostCenterSummary | None:
        """The cost center's ``cost_center_summary`` row; None when the id is unknown."""
        ...


class CostCenterSummaryUnitOfWork(UnitOfWork, Protocol):
    """The event-leftover read's transaction scope."""

    @property
    def summary(self) -> CostCenterSummaryRepository: ...
