from sqlalchemy.ext.asyncio import AsyncEngine

from mesl_finance.fees.infrastructure.repository import SqlFeeRepository
from mesl_finance.shared.infrastructure.database import SqlUnitOfWork


class SqlFeeUnitOfWork(SqlUnitOfWork):
    def __init__(self, engine: AsyncEngine, actor: str) -> None:
        super().__init__(engine, actor)
        self.fees = SqlFeeRepository(self)
