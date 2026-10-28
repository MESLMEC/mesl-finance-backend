from collections.abc import Callable

from mesl_finance.envelopes.application.ports import DraftAllocationUnitOfWork
from mesl_finance.envelopes.domain.allocation_suggestion import (
    AllocationSuggestionQuery,
    AllocationSuggestionView,
)


class DraftAllocation:
    """Business action: draft an allocation split, read in ONE transaction.

    A read: the scope closes without a commit and no open tenure is asked for
    (step 8.1 Q6=a, the 7.5 precedent).
    """

    def __init__(self, unit_of_work: Callable[[str], DraftAllocationUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(
        self, query: AllocationSuggestionQuery, actor: str
    ) -> list[AllocationSuggestionView]:
        async with self._unit_of_work(actor) as uow:
            return await uow.allocation_suggestion.suggest(query)
