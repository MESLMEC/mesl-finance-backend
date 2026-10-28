"""Application ports for the reconciliation action (ROADMAP 10.1, D-085)."""

from typing import Protocol

from mesl_finance.reconciliation.domain.reconciliation import ReconciliationView
from mesl_finance.shared.ports import UnitOfWork


class ReconciliationRepository(Protocol):
    """The single write the reconciliation slice needs."""

    async def reconcile(
        self,
        *,
        counted_total: int,
        note: str,
        counted: dict[str, int] | None,
        recorded_by: str,
    ) -> ReconciliationView:
        """Call the ``reconcile`` SQL function and return the stored row."""
        ...


class ReconciliationUnitOfWork(UnitOfWork, Protocol):
    """One transaction scope, exposing the reconciliation repository as ``.reconciliation``."""

    @property
    def reconciliation(self) -> ReconciliationRepository: ...
