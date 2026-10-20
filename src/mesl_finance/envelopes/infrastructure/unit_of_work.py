from sqlalchemy.ext.asyncio import AsyncEngine

from mesl_finance.envelopes.infrastructure.repository import SqlEnvelopeRepository
from mesl_finance.shared.infrastructure.database import SqlUnitOfWork


class SqlEnvelopeUnitOfWork(SqlUnitOfWork):
    def __init__(self, engine: AsyncEngine, actor: str) -> None:
        super().__init__(engine, actor)
        self.envelopes = SqlEnvelopeRepository(self)
