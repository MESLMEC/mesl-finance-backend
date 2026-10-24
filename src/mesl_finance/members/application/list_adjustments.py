from collections.abc import Callable

from mesl_finance.members.application.ports import AdjustmentUnitOfWork
from mesl_finance.members.domain.adjustment import AdjustmentView


class ListAdjustments:
    """Business action: one member's adjustments."""

    def __init__(self, unit_of_work: Callable[[str], AdjustmentUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, member_id: int, actor: str) -> list[AdjustmentView] | None:
        async with self._unit_of_work(actor) as uow:
            return await uow.adjustments.list_for(member_id)
