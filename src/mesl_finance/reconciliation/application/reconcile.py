"""The Reconcile use case: record one screen-vs-notes check.

Approved brief (this session): thin app. The use case passes the actor and the
three fields to the repository; PostgreSQL's ``reconcile`` function owns every
rule (db/schema.sql:1047-1087). One transaction, one commit.
"""

from collections.abc import Callable
from dataclasses import dataclass

from mesl_finance.reconciliation.application.ports import ReconciliationUnitOfWork
from mesl_finance.reconciliation.domain.reconciliation import ReconciliationView


@dataclass(frozen=True)
class ReconcileCommand:
    """What the treasurer counted against the screen."""

    counted_total: int
    note: str = ""
    counted: dict[str, int] | None = None


class Reconcile:
    """Business action: record one reconciliation in a single transaction."""

    def __init__(self, unit_of_work: Callable[[str], ReconciliationUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, command: ReconcileCommand, actor: str) -> ReconciliationView:
        async with self._unit_of_work(actor) as uow:
            view = await uow.reconciliation.reconcile(
                counted_total=command.counted_total,
                note=command.note,
                counted=command.counted,
                recorded_by=actor,
            )
            await uow.commit()
        return view
