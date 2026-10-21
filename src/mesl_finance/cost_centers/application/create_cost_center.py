from collections.abc import Callable
from dataclasses import dataclass

from mesl_finance.cost_centers.application.ports import CostCenterUnitOfWork
from mesl_finance.cost_centers.domain.cost_center import CostCenter, CostCenterView


@dataclass(frozen=True)
class CreateCostCenterCommand:
    name: str
    kind: str


class CreateCostCenter:
    """Business action: add a cost center, in ONE transaction."""

    def __init__(self, unit_of_work: Callable[[str], CostCenterUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, command: CreateCostCenterCommand, actor: str) -> CostCenterView:
        cost_center = CostCenter.create(name=command.name, kind=command.kind)
        async with self._unit_of_work(actor) as uow:
            view = await uow.cost_centers.add(cost_center)
            await uow.commit()
        return view
