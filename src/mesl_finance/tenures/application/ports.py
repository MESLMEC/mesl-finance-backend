"""Application ports for the tenure handover slice (ROADMAP 11.1)."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from mesl_finance.shared.ports import UnitOfWork
from mesl_finance.tenures.domain.snapshots import (
    AssetSnapshotView,
    HoldingSnapshotView,
    MemberSnapshotView,
)
from mesl_finance.tenures.domain.tenure import TenureView


class TenureRepository(Protocol):
    """The single write the tenure slice needs."""

    async def close(
        self,
        *,
        close_on: date,
        next_name: str,
        recorded_by: str,
    ) -> TenureView:
        """Call ``close_tenure`` and return the new tenure row."""
        ...


class TenureUnitOfWork(UnitOfWork, Protocol):
    """One transaction scope, exposing the tenure repository as ``.tenures``."""

    @property
    def tenures(self) -> TenureRepository: ...


class SnapshotRepository(Protocol):
    """The three read-only snapshot tables."""

    async def member_snapshots(self, tenure_id: int) -> list[MemberSnapshotView] | None:
        """Rows from ``tenure_member_snapshots`` for the tenure, or None if it does not exist."""
        ...

    async def asset_snapshots(self, tenure_id: int) -> list[AssetSnapshotView] | None:
        """Rows from ``tenure_asset_snapshots`` for the tenure, or None if it does not exist."""
        ...

    async def holding_snapshots(self, tenure_id: int) -> list[HoldingSnapshotView] | None:
        """Rows from ``tenure_holding_snapshots`` for the tenure, or None if it does not exist."""
        ...


class SnapshotUnitOfWork(UnitOfWork, Protocol):
    """The snapshot reads' transaction scope (the D-085 pattern)."""

    @property
    def snapshots(self) -> SnapshotRepository: ...
