"""The reconciliation read use cases (ROADMAP 10.2).

Each read opens ONE transaction, passes the JWT actor down and NEVER commits
(the 7.5 Q9=a read pattern).
"""

from collections.abc import Callable

from mesl_finance.reconciliation.application.ports import ReconciliationReadUnitOfWork
from mesl_finance.reconciliation.domain.reconciliation_reads import (
    DifferenceSuspectView,
    ReconciliationStatusView,
    UnverifiedEntryView,
)


class GetReconciliationStatus:
    def __init__(self, unit_of_work: Callable[[str], ReconciliationReadUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, actor: str) -> ReconciliationStatusView:
        async with self._unit_of_work(actor) as uow:
            return await uow.reconciliation_reads.status()


class ListUnverifiedEntries:
    def __init__(self, unit_of_work: Callable[[str], ReconciliationReadUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, actor: str) -> list[UnverifiedEntryView]:
        async with self._unit_of_work(actor) as uow:
            return await uow.reconciliation_reads.unverified_entries()


class ListDifferenceSuspects:
    def __init__(self, unit_of_work: Callable[[str], ReconciliationReadUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(
        self, difference: int, envelope_id: int | None, actor: str
    ) -> list[DifferenceSuspectView]:
        async with self._unit_of_work(actor) as uow:
            return await uow.reconciliation_reads.difference_suspects(difference, envelope_id)
