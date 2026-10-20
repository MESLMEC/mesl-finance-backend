from types import TracebackType
from typing import Any, Self

from sqlalchemy import Result, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine
from sqlalchemy.ext.asyncio.engine import AsyncTransaction

from mesl_finance.shared.infrastructure.error_mapping import map_db_error
from mesl_finance.shared.settings import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args={"server_settings": {"timezone": settings.timezone}},
    )


class SqlUnitOfWork:
    """One request = one database transaction, run as the limited app role.

    - sets `app.actor` (transaction-local) so label edits in the database are attributed;
    - maps database errors to domain errors in `execute` and `commit`;
    - rolls back unless `commit()` was called.
    """

    def __init__(self, engine: AsyncEngine, actor: str) -> None:
        self._engine = engine
        self._actor = actor
        self._conn: AsyncConnection | None = None
        self._tx: AsyncTransaction | None = None

    @property
    def actor(self) -> str:
        """The actor this transaction runs as (the `app.actor` value)."""
        return self._actor

    async def __aenter__(self) -> Self:
        self._conn = await self._engine.connect()
        self._tx = await self._conn.begin()
        await self._conn.execute(
            text("SELECT set_config('app.actor', :actor, true)"), {"actor": self._actor}
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        assert self._conn is not None  # noqa: S101
        try:
            if self._tx is not None and self._tx.is_active:
                await self._tx.rollback()
        finally:
            await self._conn.close()

    async def execute(self, sql: str, params: dict[str, Any] | None = None) -> Result[Any]:
        assert self._conn is not None  # noqa: S101
        try:
            return await self._conn.execute(text(sql), params or {})
        except DBAPIError as exc:
            mapped = map_db_error(exc)
            if mapped is None:
                raise
            raise mapped from exc

    async def commit(self) -> None:
        assert self._tx is not None  # noqa: S101
        try:  # deferred triggers (entry shape) fire here
            await self._tx.commit()
        except DBAPIError as exc:
            mapped = map_db_error(exc)
            if mapped is None:
                raise
            raise mapped from exc
