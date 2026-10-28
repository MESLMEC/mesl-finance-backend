"""Pure-Python views of the three handover snapshot tables."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class MemberSnapshotView:
    """One row from `tenure_member_snapshots`."""

    tenure_id: int
    member_id: int
    as_of: date
    weeks_owed: int
    owed: int
    credits: int
    balance: int
    weeks_overdue: int


@dataclass(frozen=True)
class AssetSnapshotView:
    """One row from `tenure_asset_snapshots`."""

    tenure_id: int
    asset_id: int
    as_of: date
    stock: int
    damaged: int
    held: int
    lost: int
    scrapped: int
    exchanged: int


@dataclass(frozen=True)
class HoldingSnapshotView:
    """One row from `tenure_holding_snapshots`."""

    tenure_id: int
    asset_id: int
    member_id: int
    quantity: int
