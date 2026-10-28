"""SQL transaction scope for the tenure handover slice."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine

from mesl_finance.shared.infrastructure.database import SqlUnitOfWork
from mesl_finance.tenures.infrastructure.repository import (
    SqlSnapshotRepository,
    SqlTenureRepository,
)


class SqlTenureUnitOfWork(SqlUnitOfWork):
    """One transaction scope carrying both tenure and snapshot repositories."""

    def __init__(self, engine: AsyncEngine, actor: str) -> None:
        super().__init__(engine, actor)
        self.tenures = SqlTenureRepository(self)
        self.snapshots = SqlSnapshotRepository(self)
