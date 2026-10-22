from sqlalchemy.ext.asyncio import AsyncEngine

from mesl_finance.members.infrastructure.repository import SqlMemberRepository
from mesl_finance.shared.infrastructure.database import SqlUnitOfWork


class SqlMemberUnitOfWork(SqlUnitOfWork):
    def __init__(self, engine: AsyncEngine, actor: str) -> None:
        super().__init__(engine, actor)
        self.members = SqlMemberRepository(self)
