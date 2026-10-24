from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from mesl_finance.fees.application.ports import FeeUnitOfWork
from mesl_finance.fees.domain.shutdown import ShutdownRange


@dataclass(frozen=True)
class SetShutdownCommand:
    from_week: date
    to_week: date
    is_shutdown: bool = True
    reason: str = ""


class SetShutdown:
    """Business action: mark or reopen whole weeks, in ONE transaction."""

    def __init__(self, unit_of_work: Callable[[str], FeeUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, command: SetShutdownCommand, actor: str) -> int:
        shutdown = ShutdownRange(
            from_week=command.from_week,
            to_week=command.to_week,
            is_shutdown=command.is_shutdown,
            reason=command.reason,
        )
        async with self._unit_of_work(actor) as uow:
            weeks = await uow.fees.set_shutdown(shutdown, recorded_by=actor)
            await uow.commit()
        return weeks
