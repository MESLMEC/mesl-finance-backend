"""Request/response schemas for the tenure handover routes (ROADMAP 11.1)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class CloseTenureRequest(BaseModel):
    """What the treasurer enters to hand over to the next committee."""

    model_config = ConfigDict(extra="forbid")

    close_on: date = Field(description="The hand-off day; never before the last recorded entry")
    next_name: str = Field(description="The new committee's tenure name")


class CloseTenureOut(BaseModel):
    """The new tenure, read back from the stored row."""

    id: int = Field(description="The new open tenure")
    name: str = Field(description="The name you chose")
    opened_on: date = Field(description="close_on + 1")


class MemberSnapshotOut(BaseModel):
    """One row from `tenure_member_snapshots` (db/schema.sql:863-872)."""

    tenure_id: int = Field(description="The closed tenure")
    member_id: int = Field(description="The member")
    as_of: date = Field(description="The close date the numbers were taken on")
    weeks_owed: int = Field(description="Billable Sundays as of the close")
    owed: int = Field(description="Whole BDT owed")
    credits: int = Field(description="Whole BDT credited")
    balance: int = Field(description="credits - owed")
    weeks_overdue: int = Field(description="Overdue weeks carried past the handover")


class AssetSnapshotOut(BaseModel):
    """One row from `tenure_asset_snapshots` (db/schema.sql:874-881)."""

    tenure_id: int = Field(description="The closed tenure")
    asset_id: int = Field(description="The asset")
    as_of: date = Field(description="The close date the counts were taken on")
    stock: int = Field(description="Units in the lab's hand")
    damaged: int = Field(description="Damaged units")
    held: int = Field(description="Units out with members")
    lost: int = Field(description="Lost units")
    scrapped: int = Field(description="Written-off units")
    exchanged: int = Field(description="Units swapped with the admin")


class HoldingSnapshotOut(BaseModel):
    """One row from `tenure_holding_snapshots` (db/schema.sql:882-888)."""

    tenure_id: int = Field(description="The closed tenure")
    asset_id: int = Field(description="The asset")
    member_id: int = Field(description="The member who still holds it")
    quantity: int = Field(description="Units held (0 hidden from the list)")
