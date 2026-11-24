from collections.abc import Callable

from mesl_finance.fees.application.ports import ShutdownStateUnitOfWork
from mesl_finance.fees.domain.shutdown import ShutdownStateView


class ListShutdownState:
    """Business action: which weeks are shut right now, in the open tenure."""

    def __init__(self, unit_of_work: Callable[[str], ShutdownStateUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, actor: str) -> list[ShutdownStateView]:
        async with self._unit_of_work(actor) as uow:
            return await uow.shutdown_state.list_current()
