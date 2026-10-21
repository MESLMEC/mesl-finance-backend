from typing import Any

from mesl_finance.cost_centers.domain.cost_center import CostCenter, CostCenterView
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
