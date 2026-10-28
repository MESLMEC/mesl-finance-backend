from collections.abc import Callable

from mesl_finance.cost_centers.application.ports import CostCenterSummaryUnitOfWork
from mesl_finance.cost_centers.domain.cost_center_summary import CostCenterSummary


class GetCostCenterSummary:
    """Business read: one event's leftover numbers, in ONE transaction, no commit."""

    def __init__(self, unit_of_work: Callable[[str], CostCenterSummaryUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, cost_center_id: int, *, actor: str) -> CostCenterSummary | None:
        async with self._unit_of_work(actor) as uow:
            return await uow.summary.get_summary(cost_center_id)
