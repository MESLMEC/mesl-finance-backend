from collections.abc import Callable

from mesl_finance.envelopes.application.ports import AllocationContextUnitOfWork
from mesl_finance.envelopes.domain.allocation_context import AllocationContextView


class GetAllocationContext:
    """Business action: the allocation screen header, read in ONE transaction.

    A read: the scope closes without a commit and no open tenure is asked for
    (step 7.5 Q9=a, the D-093 Q12 / D-105 (4) precedent).
    """

    def __init__(self, unit_of_work: Callable[[str], AllocationContextUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, actor: str) -> AllocationContextView:
        async with self._unit_of_work(actor) as uow:
            return await uow.allocation_context.get_allocation_context()
