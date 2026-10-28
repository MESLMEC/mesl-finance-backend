"""SQL adapter for the reconciliation action (ROADMAP 10.1).

Calls the SECURITY DEFINER ``reconcile`` function with bound parameters and
reads the stored row back by the returned id. JSON is passed as a string and
CAST to jsonb, mirroring the allocation adapter (D-121).
"""

import json
from typing import Any

from mesl_finance.reconciliation.domain.reconciliation import ReconciliationView
from mesl_finance.shared.infrastructure.database import SqlUnitOfWork


def _view(row: Any) -> ReconciliationView:
    return ReconciliationView(
        id=int(row["id"]),
        through_entry_id=int(row["through_entry_id"]),
        system_total=int(row["system_total"]),
        counted_total=int(row["counted_total"]),
        difference=int(row["difference"]),
        matched=bool(row["matched"]),
    )


class SqlReconciliationRepository:
    def __init__(self, uow: SqlUnitOfWork) -> None:
        self._uow = uow

    async def reconcile(
        self,
        *,
        counted_total: int,
        note: str,
        counted: dict[str, int] | None,
        recorded_by: str,
    ) -> ReconciliationView:
        result = await self._uow.execute(
            """
            SELECT reconcile(
                CAST(:recorded_by AS text),
                CAST(:counted_total AS integer),
                CAST(:note AS text),
                CAST(:counted AS jsonb)
            ) AS id
            """,
            {
                "recorded_by": recorded_by,
                "counted_total": counted_total,
                "note": note,
                "counted": None if counted is None else json.dumps(counted),
            },
        )
        row_id = int(result.scalar_one())
        result = await self._uow.execute(
            """
            SELECT id, through_entry_id, system_total, counted_total, difference, matched
            FROM reconciliations
            WHERE id = :id
            """,
            {"id": row_id},
        )
        return _view(result.mappings().one())
