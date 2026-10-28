from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from mesl_finance.envelopes.application.ports import ConfirmAllocationUnitOfWork
from mesl_finance.envelopes.domain.allocation_decision import AllocationDecision


@dataclass(frozen=True)
class ConfirmAllocationCommand:
    occurred_on: date
    note: str
    amounts: dict[str, int]


class ConfirmAllocation:
    """Business action: confirm an allocation split, in ONE transaction.

    The open tenure is asked for first so a missing one answers ``no_open_tenure``
    (step 8.2 Q5=a); ``allocate`` keeps its own check as the backstop.
    """

    def __init__(self, unit_of_work: Callable[[str], ConfirmAllocationUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, command: ConfirmAllocationCommand, actor: str) -> tuple[int, int]:
        decision = AllocationDecision(
            occurred_on=command.occurred_on,
            note=command.note,
            amounts=command.amounts,
        )
        async with self._unit_of_work(actor) as uow:
            await uow.allocations.open_tenure_id()
            entry_id, pool_balance = await uow.allocations.confirm(decision, recorded_by=actor)
            await uow.commit()
        return entry_id, pool_balance
