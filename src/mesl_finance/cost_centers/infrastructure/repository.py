from typing import Any

from mesl_finance.cost_centers.domain.cost_center import CostCenter, CostCenterView
from mesl_finance.cost_centers.domain.cost_center_summary import CostCenterSummary
from mesl_finance.cost_centers.domain.sweep import Sweep
from mesl_finance.shared.errors import NoOpenTenure
from mesl_finance.shared.infrastructure.database import SqlUnitOfWork


def _view(row: Any) -> CostCenterView:
    return CostCenterView(
        id=int(row[0]),
        name=str(row[1]),
        kind=str(row[2]),
        status=str(row[3]),
    )


class SqlCostCenterRepository:
    def __init__(self, uow: SqlUnitOfWork) -> None:
        self._uow = uow

    async def list_all(self, kind: str | None, status: str | None) -> list[CostCenterView]:
        if kind is None and status is None:
            result = await self._uow.execute(
                "SELECT id, name, kind, status FROM cost_centers ORDER BY id"
            )
        elif status is None:
            result = await self._uow.execute(
                "SELECT id, name, kind, status FROM cost_centers WHERE kind = :kind ORDER BY id",
                {"kind": kind},
            )
        elif kind is None:
            result = await self._uow.execute(
                "SELECT id, name, kind, status FROM cost_centers"
                " WHERE status = :status ORDER BY id",
                {"status": status},
            )
        else:
            result = await self._uow.execute(
                "SELECT id, name, kind, status FROM cost_centers"
                " WHERE kind = :kind AND status = :status ORDER BY id",
                {"kind": kind, "status": status},
            )
        return [_view(row) for row in result.all()]

    async def add(self, cost_center: CostCenter) -> CostCenterView:
        result = await self._uow.execute(
            """
            INSERT INTO cost_centers (name, kind, status)
            VALUES (:name, :kind, :status)
            RETURNING id, name, kind, status
            """,
            {
                "name": cost_center.name,
                "kind": cost_center.kind,
                "status": cost_center.status,
            },
        )
        return _view(result.one())

    async def rename(self, cost_center_id: int, name: str) -> CostCenterView | None:
        result = await self._uow.execute(
            """
            UPDATE cost_centers SET name = :name
            WHERE id = :id
            RETURNING id, name, kind, status
            """,
            {"id": cost_center_id, "name": name},
        )
        row = result.first()
        return None if row is None else _view(row)

    async def set_status(self, cost_center_id: int, status: str) -> CostCenterView | None:
        result = await self._uow.execute(
            """
            UPDATE cost_centers SET status = :status
            WHERE id = :id
            RETURNING id, name, kind, status
            """,
            {"id": cost_center_id, "status": status},
        )
        row = result.first()
        return None if row is None else _view(row)


class SqlSweepRepository:
    """The end-of-event sweep: ``sweep_leftover()`` (db/schema.sql:560-574, step 8.3).

    The function finds the tenure, the pool and the leftover itself and writes the
    ``sweep`` header (with the cost center) and both lines, so the adapter only
    passes the five bound parameters and reads the balances back.
    """

    def __init__(self, uow: SqlUnitOfWork) -> None:
        self._uow = uow

    async def open_tenure_id(self) -> int:
        row = (await self._uow.execute("SELECT id FROM tenures WHERE closed_on IS NULL")).first()
        if row is None:
            raise NoOpenTenure("there is no open tenure; the owner must create one first")
        return int(row[0])

    async def sweep(self, sweep: Sweep, recorded_by: str) -> tuple[int, int, int]:
        result = await self._uow.execute(
            """
            SELECT sweep_leftover(
                CAST(:cost_center_id AS bigint), CAST(:from_envelope_id AS bigint),
                CAST(:recorded_by AS text), CAST(:occurred_on AS date), CAST(:note AS text)
            )
            """,
            {
                "cost_center_id": sweep.cost_center_id,
                "from_envelope_id": sweep.from_envelope_id,
                "recorded_by": recorded_by,
                "occurred_on": sweep.occurred_on,
                "note": sweep.note,
            },
        )
        entry_id = int(result.scalar_one())
        balances = await self._uow.execute(
            """
            SELECT
                (SELECT balance FROM envelope_balances
                  WHERE id = :from_envelope_id) AS from_balance,
                (SELECT balance FROM envelope_balances
                  WHERE id = (SELECT id FROM envelopes WHERE is_pool)) AS pool_balance
            """,
            {"from_envelope_id": sweep.from_envelope_id},
        )
        row = balances.mappings().one()
        return entry_id, int(row["from_balance"]), int(row["pool_balance"])


class SqlCostCenterSummaryRepository:
    """The event-leftover read: one ``cost_center_summary`` row (db/schema.sql:537-557)."""

    def __init__(self, uow: SqlUnitOfWork) -> None:
        self._uow = uow

    async def get_summary(self, cost_center_id: int) -> CostCenterSummary | None:
        result = await self._uow.execute(
            """
            SELECT cost_center_id, name, kind, status, money_in, money_out, swept, leftover
              FROM cost_center_summary
             WHERE cost_center_id = :cost_center_id
            """,
            {"cost_center_id": cost_center_id},
        )
        row = result.mappings().first()
        if row is None:
            return None
        return CostCenterSummary(
            cost_center_id=int(row["cost_center_id"]),
            name=str(row["name"]),
            kind=str(row["kind"]),
            status=str(row["status"]),
            money_in=int(row["money_in"]),
            money_out=int(row["money_out"]),
            swept=int(row["swept"]),
            leftover=int(row["leftover"]),
        )
