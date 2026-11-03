"""Request/response schemas for the tenure handover routes (ROADMAP 11.1)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class CloseTenureRequest(BaseModel):
    """What the treasurer enters to hand over to the next committee."""

    model_config = ConfigDict(extra="forbid")

    close_on: date
    next_name: str


class CloseTenureOut(BaseModel):
    """The new tenure, read back from the stored row."""

    id: int
    name: str
    opened_on: date


class TenureOut(BaseModel):
    """One row from `tenures` (db/schema.sql:29-39)."""

    id: int
    name: str
    opened_on: date
    closed_on: date | None = None
    closed_at: datetime | None = None
    closing_checksum: str | None = None


class MemberSnapshotOut(BaseModel):
    """One row from `tenure_member_snapshots` (db/schema.sql:863-872)."""

    tenure_id: int
    member_id: int
    as_of: date
    weeks_owed: int
    owed: int
    credits: int
    balance: int
    weeks_overdue: int


class AssetSnapshotOut(BaseModel):
    """One row from `tenure_asset_snapshots` (db/schema.sql:874-881)."""

    tenure_id: int
    asset_id: int
    as_of: date
    stock: int
    damaged: int
    held: int
    lost: int
    scrapped: int
    exchanged: int


class HoldingSnapshotOut(BaseModel):
    """One row from `tenure_holding_snapshots` (db/schema.sql:882-888)."""

    tenure_id: int
    asset_id: int
    member_id: int
    quantity: int
