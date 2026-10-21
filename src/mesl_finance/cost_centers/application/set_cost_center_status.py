from collections.abc import Callable

from mesl_finance.cost_centers.application.ports import CostCenterUnitOfWork
from mesl_finance.cost_centers.domain.cost_center import CostCenterView


class SetCostCenterStatus:
    """Business action: replace one cost center's status, in ONE transaction."""

    def __init__(self, unit_of_work: Callable[[str], CostCenterUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, cost_center_id: int, status: str, actor: str) -> CostCenterView | None:
        async with self._unit_of_work(actor) as uow:
            view = await uow.cost_centers.set_status(cost_center_id, status)
            await uow.commit()
        return view
