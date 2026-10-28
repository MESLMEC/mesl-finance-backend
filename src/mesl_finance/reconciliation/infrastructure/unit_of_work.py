"""SQL transaction scope for the reconciliation slice."""

from sqlalchemy.ext.asyncio import AsyncEngine

from mesl_finance.reconciliation.infrastructure.repository import (
    SqlReconciliationReadRepository,
    SqlReconciliationRepository,
)
from mesl_finance.shared.infrastructure.database import SqlUnitOfWork


class SqlReconciliationUnitOfWork(SqlUnitOfWork):
    def __init__(self, engine: AsyncEngine, actor: str) -> None:
        super().__init__(engine, actor)
        self.reconciliation = SqlReconciliationRepository(self)
        self.reconciliation_reads = SqlReconciliationReadRepository(self)
