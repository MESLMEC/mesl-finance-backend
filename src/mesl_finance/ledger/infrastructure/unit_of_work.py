from sqlalchemy.ext.asyncio import AsyncEngine

from mesl_finance.ledger.infrastructure.repository import SqlLedgerRepository
from mesl_finance.shared.infrastructure.database import SqlUnitOfWork


class SqlLedgerUnitOfWork(SqlUnitOfWork):
    def __init__(self, engine: AsyncEngine, actor: str) -> None:
        super().__init__(engine, actor)
        self.ledger = SqlLedgerRepository(self)
