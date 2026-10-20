"""Ports of the shared kernel (roadmap step 2.2).

Pure Python: no fastapi, sqlalchemy, asyncpg or pydantic import is allowed
here (Phase 2 rule, ROADMAP.md). Features depend on these ports in their
application layer; feature-level protocols extend `UnitOfWork` and add their
own repository accessors (see `ledger/application/ports.py`).
"""

from datetime import datetime
from types import TracebackType
from typing import Protocol, Self, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    """A time source for the application layer (no wall clock of its own)."""

    def now(self) -> datetime:
        """The current instant, timezone-aware, in UTC."""
        ...


@runtime_checkable
class UnitOfWork(Protocol):
    """One use case = one database transaction.

    Transaction scope plus the actor only (approved brief, Q3=a): repository
    accessors are declared by each feature's own protocol.
    """

    @property
    def actor(self) -> str:
        """The actor the transaction runs as (set as `app.actor`)."""
        ...

    async def __aenter__(self) -> Self:
        """Open the transaction scope."""
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Close the commit scope."""
        ...

    async def commit(self) -> None:
        """Commit the transaction; raises domain errors mapped at commit time."""
        ...
