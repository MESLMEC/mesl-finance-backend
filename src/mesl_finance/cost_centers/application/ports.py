from typing import Protocol

from mesl_finance.cost_centers.domain.cost_center import CostCenter, CostCenterView
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
