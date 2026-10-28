import json
from typing import Any

from mesl_finance.envelopes.domain.allocation_context import AllocationContextView
from mesl_finance.envelopes.domain.allocation_decision import AllocationDecision
from mesl_finance.envelopes.domain.allocation_suggestion import (
    AllocationSuggestionQuery,
    AllocationSuggestionView,
)
from mesl_finance.envelopes.domain.envelope import Envelope, EnvelopeView
from mesl_finance.shared.errors import NoOpenTenure
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


class SqlDraftAllocationRepository:
    """The allocation draft read: ``allocation_suggestion()`` (step 8.1 Q1=a)."""

    def __init__(self, uow: SqlUnitOfWork) -> None:
        self._uow = uow

    async def suggest(self, query: AllocationSuggestionQuery) -> list[AllocationSuggestionView]:
        result = await self._uow.execute(
            """
            SELECT envelope_id, envelope_name, balance, target_cap, alloc_priority,
                   gap, phase, suggested
            FROM allocation_suggestion(
                CAST(:amount AS integer), CAST(:shares AS jsonb)
            )
            """,
            {
                "amount": query.amount,
                "shares": None if query.shares is None else json.dumps(query.shares),
            },
        )
        return [_suggestion(row) for row in result.mappings().all()]


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)


def _suggestion(row: Any) -> AllocationSuggestionView:
    return AllocationSuggestionView(
        envelope_id=int(row["envelope_id"]),
        envelope_name=str(row["envelope_name"]),
        balance=int(row["balance"]),
        target_cap=_optional_int(row["target_cap"]),
        alloc_priority=_optional_int(row["alloc_priority"]),
        gap=_optional_int(row["gap"]),
        phase=str(row["phase"]),
        suggested=int(row["suggested"]),
    )


class SqlConfirmAllocationRepository:
    """The allocation confirmation: ``allocate()`` (step 8.2 Q1=a).

    The function writes the ``transfer`` header (``tag='allocation'``), the lines
    and the ``allocation_sessions`` row itself, so the adapter only passes the four
    bound parameters and reads the pool balance back.
    """

    def __init__(self, uow: SqlUnitOfWork) -> None:
        self._uow = uow

    async def open_tenure_id(self) -> int:
        row = (await self._uow.execute("SELECT id FROM tenures WHERE closed_on IS NULL")).first()
        if row is None:
            raise NoOpenTenure("there is no open tenure; the owner must create one first")
        return int(row[0])

    async def confirm(self, decision: AllocationDecision, recorded_by: str) -> tuple[int, int]:
        result = await self._uow.execute(
            """
            SELECT allocate(
                CAST(:recorded_by AS text), CAST(:occurred_on AS date),
                CAST(:note AS text), CAST(:amounts AS jsonb)
            )
            """,
            {
                "recorded_by": recorded_by,
                "occurred_on": decision.occurred_on,
                "note": decision.note,
                "amounts": json.dumps(decision.amounts),
            },
        )
        entry_id = int(result.scalar_one())
        balance = await self._uow.execute(
            """
            SELECT balance FROM envelope_balances
             WHERE id = (SELECT id FROM envelopes WHERE is_pool)
            """
        )
        return entry_id, int(balance.scalar_one())
