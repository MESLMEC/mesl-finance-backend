from typing import Any

from mesl_finance.envelopes.domain.allocation_context import AllocationContextView
from mesl_finance.envelopes.domain.envelope import Envelope, EnvelopeView
from mesl_finance.shared.infrastructure.database import SqlUnitOfWork


def _view(row: Any) -> EnvelopeView:
    return EnvelopeView(
        id=int(row[0]),
        name=str(row[1]),
        target_cap=row[2],
        alloc_priority=row[3],
        is_pool=bool(row[4]),
        active=bool(row[5]),
    )


class SqlEnvelopeRepository:
    def __init__(self, uow: SqlUnitOfWork) -> None:
        self._uow = uow

    async def list_all(self) -> list[EnvelopeView]:
        result = await self._uow.execute(
            """
            SELECT id, name, target_cap, alloc_priority, is_pool, active
            FROM envelopes
            ORDER BY id
            """
        )
        return [_view(row) for row in result.all()]

    async def add(self, envelope: Envelope) -> EnvelopeView:
        result = await self._uow.execute(
            """
            INSERT INTO envelopes (name, target_cap, alloc_priority)
            VALUES (:name, :target_cap, :alloc_priority)
            RETURNING id, name, target_cap, alloc_priority, is_pool, active
            """,
            {
                "name": envelope.name,
                "target_cap": envelope.target_cap,
                "alloc_priority": envelope.alloc_priority,
            },
        )
        return _view(result.one())

    async def rename(self, envelope_id: int, name: str) -> EnvelopeView | None:
        result = await self._uow.execute(
            """
            UPDATE envelopes SET name = :name
            WHERE id = :id
            RETURNING id, name, target_cap, alloc_priority, is_pool, active
            """,
            {"id": envelope_id, "name": name},
        )
        row = result.first()
        return None if row is None else _view(row)

    async def update_settings(
        self, envelope_id: int, target_cap: int | None, alloc_priority: int | None
    ) -> EnvelopeView | None:
        result = await self._uow.execute(
            """
            UPDATE envelopes SET target_cap = :target_cap, alloc_priority = :alloc_priority
            WHERE id = :id
            RETURNING id, name, target_cap, alloc_priority, is_pool, active
            """,
            {"id": envelope_id, "target_cap": target_cap, "alloc_priority": alloc_priority},
        )
        row = result.first()
        return None if row is None else _view(row)

    async def deactivate(self, envelope_id: int) -> EnvelopeView | None:
        result = await self._uow.execute(
            """
            UPDATE envelopes SET active = false
            WHERE id = :id
            RETURNING id, name, target_cap, alloc_priority, is_pool, active
            """,
            {"id": envelope_id},
        )
        row = result.first()
        return None if row is None else _view(row)


class SqlAllocationContextRepository:
    """The allocation header read: the ``allocation_context`` view (step 7.5 Q5=a)."""

    def __init__(self, uow: SqlUnitOfWork) -> None:
        self._uow = uow

    async def get_allocation_context(self) -> AllocationContextView:
        result = await self._uow.execute(
            """
            SELECT pool_balance, member_credit_held, pool_after_member_credit
            FROM allocation_context
            """
        )
        row = result.mappings().one()
        return AllocationContextView(
            pool_balance=int(row["pool_balance"]),
            member_credit_held=int(row["member_credit_held"]),
            pool_after_member_credit=int(row["pool_after_member_credit"]),
        )
