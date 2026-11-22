"""The SQL adapter for the shared idempotency keys (issue #4, slice 1).

Claim-first (the approved Q2=a): a write claims its key at the start of its
transaction, so a concurrent retry of the same key cannot slip through; the
result is filled in only after the write succeeded, in the same transaction, so
a failed write leaves the key free. The stored result is the use case's result
value; the caller replays it verbatim.

PostgreSQL is the uniqueness authority: the primary key (actor, key) makes a
second claim of the same key a no-op that reads the first row back. That is why
the actor is read from the transaction (`SqlUnitOfWork.actor`) rather than
passed in.

Library/SQL facts verified this session (AGENTS.md section 3):
- sqlalchemy/ext/asyncio/engine.py: AsyncConnection.execute(text, params) takes
  bound parameters and returns a buffered Result; `.mappings().first()` and
  `.first()` are already the repository's own read pattern (D-089);
- PostgreSQL `INSERT ... ON CONFLICT (actor, key) DO NOTHING RETURNING 1` and
  `CAST(:value AS jsonb)` are standard SQL; the table and its columns are the
  approved DDL in db/sql/0003_idempotency_keys.sql.
"""

import json
from typing import Any, Protocol

from sqlalchemy import Result

from mesl_finance.shared.errors import IdempotencyConflict
from mesl_finance.shared.idempotency import IdempotencyStore


class _Executor(Protocol):
    """What the store needs from the unit of work it shares a transaction with."""

    @property
    def actor(self) -> str: ...

    async def execute(self, sql: str, params: dict[str, Any] | None = None) -> Result[Any]: ...


class SqlIdempotencyStore(IdempotencyStore):
    def __init__(self, executor: _Executor) -> None:
        self._executor = executor

    async def claim(self, key: str, fingerprint: str) -> Any:
        inserted = await self._executor.execute(
            """
            INSERT INTO idempotency_keys (actor, key, request_hash, result)
            VALUES (:actor, :key, :fingerprint, NULL)
            ON CONFLICT (actor, key) DO NOTHING
            RETURNING 1
            """,
            {"actor": self._executor.actor, "key": key, "fingerprint": fingerprint},
        )
        if inserted.first() is not None:
            return None
        stored = (
            (
                await self._executor.execute(
                    """
                    SELECT request_hash, CAST(result AS text) AS result_text
                      FROM idempotency_keys
                     WHERE actor = :actor AND key = :key
                    """,
                    {"actor": self._executor.actor, "key": key},
                )
            )
            .mappings()
            .first()
        )
        if stored is None:
            # The conflicting row vanished between the insert and the read
            # (only possible if it was rolled back); treat the key as free.
            return None
        if stored["request_hash"] != fingerprint:
            raise IdempotencyConflict(
                f"idempotency key {key!r} was already used with a different request"
            )
        raw = stored["result_text"]
        return None if raw is None else json.loads(raw)

    async def remember(self, key: str, result: Any) -> None:
        await self._executor.execute(
            """
            UPDATE idempotency_keys
               SET result = CAST(:result AS jsonb)
             WHERE actor = :actor AND key = :key
            """,
            {"actor": self._executor.actor, "key": key, "result": json.dumps(result)},
        )

    async def result_for(self, key: str) -> Any:
        row = (
            await self._executor.execute(
                """
                SELECT CAST(result AS text) AS result_text
                  FROM idempotency_keys
                 WHERE actor = :actor AND key = :key
                """,
                {"actor": self._executor.actor, "key": key},
            )
        ).first()
        if row is None:
            return None
        raw = row[0]
        return None if raw is None else json.loads(raw)
