from collections.abc import Callable

from mesl_finance.fees.application.ports import FeeUnitOfWork
from mesl_finance.fees.domain.shutdown import ShutdownEventView


class ListShutdownEvents:
    """Business action: the shutdown history, in week_start and id order."""

    def __init__(self, unit_of_work: Callable[[str], FeeUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, actor: str) -> list[ShutdownEventView]:
        async with self._unit_of_work(actor) as uow:
            return await uow.fees.list_shutdown_events()
