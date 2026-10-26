from collections.abc import Callable

from mesl_finance.fees.application.ports import DuesUnitOfWork
from mesl_finance.fees.domain.dues import StandingView


class ListDues:
    """Business action: the dues overview, read in ONE transaction.

    A read: the scope closes without a commit and no open tenure is asked for
    (step 7.5 Q9=a, the D-093 Q12 / D-105 (4) precedent).
    """

    def __init__(self, unit_of_work: Callable[[str], DuesUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, actor: str) -> list[StandingView]:
        async with self._unit_of_work(actor) as uow:
            return await uow.dues.list_dues()
