"""SQL adapters for the tenure handover slice (ROADMAP 11.1)."""

from __future__ import annotations

from datetime import date
from typing import Any

from mesl_finance.shared.infrastructure.database import SqlUnitOfWork
from mesl_finance.tenures.domain.snapshots import (
    AssetSnapshotView,
    HoldingSnapshotView,
    MemberSnapshotView,
)
from mesl_finance.tenures.domain.tenure import TenureView


def _tenure_view(row: Any) -> TenureView:
    return TenureView(
        id=int(row["id"]),
        name=str(row["name"]),
        opened_on=row["opened_on"],
    )


def _member_snapshot(row: Any) -> MemberSnapshotView:
    return MemberSnapshotView(
        tenure_id=int(row["tenure_id"]),
        member_id=int(row["member_id"]),
        as_of=row["as_of"],
        weeks_owed=int(row["weeks_owed"]),
        owed=int(row["owed"]),
        credits=int(row["credits"]),
        balance=int(row["balance"]),
        weeks_overdue=int(row["weeks_overdue"]),
    )


def _asset_snapshot(row: Any) -> AssetSnapshotView:
    return AssetSnapshotView(
        tenure_id=int(row["tenure_id"]),
        asset_id=int(row["asset_id"]),
        as_of=row["as_of"],
        stock=int(row["stock"]),
        damaged=int(row["damaged"]),
        held=int(row["held"]),
        lost=int(row["lost"]),
        scrapped=int(row["scrapped"]),
        exchanged=int(row["exchanged"]),
    )


def _holding_snapshot(row: Any) -> HoldingSnapshotView:
    return HoldingSnapshotView(
        tenure_id=int(row["tenure_id"]),
        asset_id=int(row["asset_id"]),
        member_id=int(row["member_id"]),
        quantity=int(row["quantity"]),
    )


class SqlTenureRepository:
    """Calls the SECURITY DEFINER ``close_tenure`` function with bound parameters."""

    def __init__(self, uow: SqlUnitOfWork) -> None:
        self._uow = uow

    async def close(
        self,
        *,
        close_on: date,
        next_name: str,
        recorded_by: str,
    ) -> TenureView:
        result = await self._uow.execute(
            """
            SELECT close_tenure(
                CAST(:close_on AS date),
                CAST(:recorded_by AS text),
                CAST(:next_name AS text)
            ) AS id
            """,
            {
                "close_on": close_on,
                "recorded_by": recorded_by,
                "next_name": next_name,
            },
        )
        row_id = int(result.scalar_one())
        result = await self._uow.execute(
            "SELECT id, name, opened_on FROM tenures WHERE id = :id",
            {"id": row_id},
        )
        return _tenure_view(result.mappings().one())


class SqlSnapshotRepository:
    """Direct reads from the three append-only snapshot tables."""

    def __init__(self, uow: SqlUnitOfWork) -> None:
        self._uow = uow

    async def _tenure_exists(self, tenure_id: int) -> bool:
        result = await self._uow.execute(
            "SELECT 1 FROM tenures WHERE id = :id",
            {"id": tenure_id},
        )
        return result.first() is not None

    async def member_snapshots(self, tenure_id: int) -> list[MemberSnapshotView] | None:
        if not await self._tenure_exists(tenure_id):
            return None
        result = await self._uow.execute(
            """
            SELECT tenure_id, member_id, as_of, weeks_owed, owed, credits, balance, weeks_overdue
              FROM tenure_member_snapshots
             WHERE tenure_id = :tenure_id
             ORDER BY tenure_id, member_id
            """,
            {"tenure_id": tenure_id},
        )
        return [_member_snapshot(row) for row in result.mappings().all()]

    async def asset_snapshots(self, tenure_id: int) -> list[AssetSnapshotView] | None:
        if not await self._tenure_exists(tenure_id):
            return None
        result = await self._uow.execute(
            """
            SELECT tenure_id, asset_id, as_of, stock, damaged, held, lost, scrapped, exchanged
              FROM tenure_asset_snapshots
             WHERE tenure_id = :tenure_id
             ORDER BY tenure_id, asset_id
            """,
            {"tenure_id": tenure_id},
        )
        return [_asset_snapshot(row) for row in result.mappings().all()]

    async def holding_snapshots(self, tenure_id: int) -> list[HoldingSnapshotView] | None:
        if not await self._tenure_exists(tenure_id):
            return None
        result = await self._uow.execute(
            """
            SELECT tenure_id, asset_id, member_id, quantity
              FROM tenure_holding_snapshots
             WHERE tenure_id = :tenure_id
             ORDER BY tenure_id, asset_id, member_id
            """,
            {"tenure_id": tenure_id},
        )
        return [_holding_snapshot(row) for row in result.mappings().all()]
