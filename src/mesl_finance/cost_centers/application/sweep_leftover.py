from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from mesl_finance.cost_centers.application.ports import SweepUnitOfWork
from mesl_finance.cost_centers.domain.sweep import Sweep


@dataclass(frozen=True)
class SweepCommand:
    cost_center_id: int
    from_envelope_id: int
    occurred_on: date
    note: str


class SweepLeftover:
    """Business action: sweep an event's leftover back to the pool, ONE transaction.

    The open tenure is asked for first so a missing one answers ``no_open_tenure``
    (the step 8.2 Q5=a pattern); ``sweep_leftover`` keeps its own check as the
    backstop.
    """

    def __init__(self, unit_of_work: Callable[[str], SweepUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, command: SweepCommand, actor: str) -> tuple[int, int, int]:
        sweep = Sweep(
            cost_center_id=command.cost_center_id,
            from_envelope_id=command.from_envelope_id,
            occurred_on=command.occurred_on,
            note=command.note,
        )
        async with self._unit_of_work(actor) as uow:
            await uow.sweeps.open_tenure_id()
            entry_id, from_balance, pool_balance = await uow.sweeps.sweep(sweep, recorded_by=actor)
            await uow.commit()
        return entry_id, from_balance, pool_balance
