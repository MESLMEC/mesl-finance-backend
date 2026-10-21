from collections.abc import Callable

from mesl_finance.cost_centers.application.ports import CostCenterUnitOfWork
from mesl_finance.cost_centers.domain.cost_center import CostCenterView


class ListCostCenters:
    """Business action: the treasurer's cost-center list, optionally filtered."""

    def __init__(self, unit_of_work: Callable[[str], CostCenterUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(
        self, actor: str, kind: str | None = None, status: str | None = None
    ) -> list[CostCenterView]:
        async with self._unit_of_work(actor) as uow:
            return await uow.cost_centers.list_all(kind, status)
