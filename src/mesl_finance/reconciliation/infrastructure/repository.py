"""SQL adapter for the reconciliation action (ROADMAP 10.1).

Calls the SECURITY DEFINER ``reconcile`` function with bound parameters and
reads the stored row back by the returned id. JSON is passed as a string and
CAST to jsonb, mirroring the allocation adapter (D-121).
"""

import json
from typing import Any

from mesl_finance.reconciliation.domain.reconciliation import ReconciliationView
from mesl_finance.reconciliation.domain.reconciliation_reads import (
    DifferenceSuspectView,
    ReconciliationStatusView,
    UnverifiedEntryView,
)
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


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)


class SqlReconciliationReadRepository:
    def __init__(self, uow: SqlUnitOfWork) -> None:
        self._uow = uow

    async def status(self) -> ReconciliationStatusView:
        """`reconciliation_status` (db/schema.sql:1110-1116): always one row."""
        result = await self._uow.execute(
            """
            SELECT last_match_id, last_match_date, last_match_through_entry,
                   days_since_last_match, entries_since_last_match,
                   latest_attempt_matched, latest_difference
              FROM reconciliation_status
            """
        )
        row = result.mappings().one()
        return ReconciliationStatusView(
            last_match_id=_optional_int(row["last_match_id"]),
            last_match_date=row["last_match_date"],
            last_match_through_entry=_optional_int(row["last_match_through_entry"]),
            days_since_last_match=_optional_int(row["days_since_last_match"]),
            entries_since_last_match=int(row["entries_since_last_match"]),
            latest_attempt_matched=None
            if row["latest_attempt_matched"] is None
            else bool(row["latest_attempt_matched"]),
            latest_difference=_optional_int(row["latest_difference"]),
        )

    async def unverified_entries(self) -> list[UnverifiedEntryView]:
        """`unverified_entries` (db/schema.sql:1095-1108), in the view's own order."""
        result = await self._uow.execute(
            """
            SELECT id, tenure_id, kind::text AS kind, occurred_on, recorded_at, recorded_by,
                   note, tag, cost_center_id, member_id, reverses_id, is_voided,
                   net_effect, size
              FROM unverified_entries
            """
        )
        return [
            UnverifiedEntryView(
                id=int(row["id"]),
                tenure_id=int(row["tenure_id"]),
                kind=str(row["kind"]),
                occurred_on=row["occurred_on"],
                recorded_at=row["recorded_at"],
                recorded_by=str(row["recorded_by"]),
                note=str(row["note"]),
                tag=None if row["tag"] is None else str(row["tag"]),
                cost_center_id=_optional_int(row["cost_center_id"]),
                member_id=_optional_int(row["member_id"]),
                reverses_id=_optional_int(row["reverses_id"]),
                is_voided=bool(row["is_voided"]),
                net_effect=int(row["net_effect"]),
                size=int(row["size"]),
            )
            for row in result.mappings().all()
        ]

    async def difference_suspects(
        self, difference: int, envelope_id: int | None
    ) -> list[DifferenceSuspectView]:
        """`difference_suspects(p_diff, p_envelope)` (db/schema.sql:1122-1157)."""
        result = await self._uow.execute(
            """
            SELECT entry_id, kind::text AS kind, occurred_on, effect, note, why
              FROM difference_suspects(
                CAST(:difference AS integer), CAST(:envelope_id AS bigint)
              )
            """,
            {"difference": difference, "envelope_id": envelope_id},
        )
        return [
            DifferenceSuspectView(
                entry_id=int(row["entry_id"]),
                kind=str(row["kind"]),
                occurred_on=row["occurred_on"],
                effect=int(row["effect"]),
                note=str(row["note"]),
                why=str(row["why"]),
            )
            for row in result.mappings().all()
        ]
