"""Application ports for the reconciliation action (ROADMAP 10.1, D-085)."""

from typing import Protocol

from mesl_finance.reconciliation.domain.reconciliation import ReconciliationView
from mesl_finance.reconciliation.domain.reconciliation_reads import (
    DifferenceSuspectView,
    ReconciliationStatusView,
    UnverifiedEntryView,
)
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


class ReconciliationReadRepository(Protocol):
    """The three read-only views and functions behind the reconciliation reads."""

    async def status(self) -> ReconciliationStatusView:
        """The single `reconciliation_status` row."""
        ...

    async def unverified_entries(self) -> list[UnverifiedEntryView]:
        """Entries recorded after the last match, in the view's own order."""
        ...

    async def difference_suspects(
        self, difference: int, envelope_id: int | None
    ) -> list[DifferenceSuspectView]:
        """`difference_suspects(difference, envelope_id)`, in the function's own order."""
        ...


class ReconciliationReadUnitOfWork(UnitOfWork, Protocol):
    """The reconciliation reads' transaction scope (the D-085 pattern)."""

    @property
    def reconciliation_reads(self) -> ReconciliationReadRepository: ...
