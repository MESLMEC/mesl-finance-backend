from collections.abc import Callable

from mesl_finance.cost_centers.application.ports import CostCenterUnitOfWork
from mesl_finance.cost_centers.domain.cost_center import CostCenterView, require_name


class RenameCostCenter:
    """Business action: rename one cost center, in ONE transaction. Kind never changes."""

    def __init__(self, unit_of_work: Callable[[str], CostCenterUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, cost_center_id: int, name: str, actor: str) -> CostCenterView | None:
        require_name(name)  # the blank-name rule lives in the domain
        async with self._unit_of_work(actor) as uow:
            view = await uow.cost_centers.rename(cost_center_id, name)
            await uow.commit()
        return view
