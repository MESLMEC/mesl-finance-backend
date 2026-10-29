from collections.abc import Callable

from mesl_finance.ledger.application.ports import EntryListUnitOfWork
from mesl_finance.ledger.domain.entry_list import EntryView, LedgerLineView, ListEntriesQuery


class ListEntries:
    """Business action: the treasurer's list, read in ONE transaction.

    A read: the scope closes without a commit (step 6.7 Q12=a) and no open
    tenure is asked for, because every tenure is listed by default (Q4=a).
    """

    def __init__(self, unit_of_work: Callable[[str], EntryListUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, query: ListEntriesQuery, actor: str) -> list[EntryView]:
        async with self._unit_of_work(actor) as uow:
            return await uow.ledger.list_entries(query)

    async def list_lines(self, tenure_id: int | None, actor: str) -> list[LedgerLineView]:
        async with self._unit_of_work(actor) as uow:
            return await uow.ledger.list_lines(tenure_id)

