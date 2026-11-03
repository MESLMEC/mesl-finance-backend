from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from mesl_finance.assets.domain.asset import AssetMode, AssetOwner
from mesl_finance.assets.domain.asset_event import AcquireSource, AssetEventKind


class AssetOut(BaseModel):
    id: int = Field(description="The asset")
    name: str = Field(description="The human label")
    mode: str = Field(description="individual (one unit per row) | counted (a quantity per row)")
    ownership: str = Field(description="admin (college-provided) | lab (lab money)")
    tag: str | None = Field(
        description="Admin inventory tag / lab tag / serial; case-insensitive UNIQUE"
    )
    note: str = Field(description="Free notes")


class CreateAssetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Blank refused app-side (422)")
    mode: AssetMode = Field(description="See AssetOut.mode")
    ownership: AssetOwner = Field(description="See AssetOut.ownership")
    tag: str | None = Field(default=None, description="Optional; unique if present")
    note: str = Field(default="", description="Optional")


class EditAssetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, description="Omit = unchanged; blank refused")
    tag: str | None = Field(default=None, description="Omit = unchanged; explicit null clears")
    note: str | None = Field(default=None, description="Omit = unchanged")
    mode: AssetMode | None = Field(
        default=None, description="Refused with 409 once the asset has events"
    )
    ownership: AssetOwner | None = Field(
        default=None, description="Refused with 409 once the asset has events"
    )


class AssetEventOut(BaseModel):
    """The event as stored; `ledger_transaction_id` names the expense that
    paid for a `purchase` (issue #10)."""

    id: int = Field(description="The event")
    asset_id: int = Field(description="Which asset it touched")
    kind: str = Field(description="One of the nine kinds")
    quantity: int = Field(description="NON-ZERO; the direction follows the kind")
    occurred_on: date = Field(description="The day it happened (inside the open tenure)")
    note: str = Field(description="Required on damaged/lost: cause is free text")
    ledger_transaction_id: int | None = Field(
        description="Set on purchase acquisitions: the paying ledger entry"
    )


class AssetEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: AssetEventKind = Field(description="The nine kinds")
    quantity: int = Field(strict=True, description="Whole number ≠ 0")
    occurred_on: date = Field(description="Inside the open tenure")
    member_id: int | None = Field(
        default=None, description="The borrower (or holder for damaged/lost); forbids lend-to-none"
    )
    source: AcquireSource | None = Field(
        default=None,
        description="ACQUIRED only: purchase, admin, project_return, donation, replacement, other",
    )
    ledger_transaction_id: int | None = Field(
        default=None,
        description="REQUIRED on purchase acquisitions: the ledger expense that paid (D-163)",
    )
    note: str = Field(default="", description="Free; broken/lost cause goes here")


class FixEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantity: int = Field(strict=True, description="The CORRECTED count")
    occurred_on: date = Field(description="Written on both rows")
    note: str = Field(default="", description="Why it was corrected")


class FixEventOut(BaseModel):
    id: int = Field(description="The replacement event")
    asset_id: int = Field(description="The asset")
    kind: str = Field(description="The original's kind")
    quantity: int = Field(description="The replacement's quantity")
    occurred_on: date = Field(description="As the request said")
    note: str = Field(description="The ORIGINAL's note, kept")
    reversal_id: int = Field(description="The mirror event voiding the original")
    ledger_transaction_id: int | None = Field(description="copied through from the original")


class AssetStateOut(BaseModel):
    asset_id: int = Field(description="The asset")
    asset_name: str = Field(description="Its CURRENT name (renames show here)")
    ownership: str = Field(description="admin | lab")
    mode: str = Field(description="individual | counted")
    tag: str | None = Field(description="Its unique tag, if any")
    stock: int = Field(description="Units in the lab's hand")
    damaged: int = Field(description="Units damaged")
    with_members: int = Field(description="Units lent out to members")
    lost: int = Field(description="Units lost")
    scrapped: int = Field(description="Units written off")
    exchanged: int = Field(description="Units swapped with the admin")


class WhoHasWhatOut(BaseModel):
    asset_id: int = Field(description="The asset")
    asset_name: str = Field(description="Its current name")
    member_id: int = Field(description="The holder")
    member_name: str = Field(description="Shown in the report")
    quantity: int = Field(description="How many they hold right now")


class AssetActivityOut(BaseModel):
    asset_name: str = Field(description="Its current name")
    ownership: str = Field(description="admin | lab")
    kind: str = Field(description="The grouped event kind")
    source: str | None = Field(description="acquired rows only: purchase/admin/...")
    units: int = Field(description="Units moved by this row")
    events: int = Field(description="How many events the row folds (fixes collapse)")
