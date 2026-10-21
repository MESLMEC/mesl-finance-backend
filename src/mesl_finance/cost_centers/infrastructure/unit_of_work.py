from sqlalchemy.ext.asyncio import AsyncEngine

from mesl_finance.cost_centers.infrastructure.repository import SqlCostCenterRepository
from mesl_finance.shared.infrastructure.database import SqlUnitOfWork


class SqlCostCenterUnitOfWork(SqlUnitOfWork):
    def __init__(self, engine: AsyncEngine, actor: str) -> None:
        super().__init__(engine, actor)
        self.cost_centers = SqlCostCenterRepository(self)
