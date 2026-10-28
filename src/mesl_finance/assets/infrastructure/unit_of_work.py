from sqlalchemy.ext.asyncio import AsyncEngine

from mesl_finance.assets.infrastructure.repository import (
    SqlAssetRepository,
    SqlFixEventRepository,
)
from mesl_finance.shared.infrastructure.database import SqlUnitOfWork


class SqlAssetUnitOfWork(SqlUnitOfWork):
    def __init__(self, engine: AsyncEngine, actor: str) -> None:
        super().__init__(engine, actor)
        self.assets = SqlAssetRepository(self)
        self.fix_events = SqlFixEventRepository(self)
