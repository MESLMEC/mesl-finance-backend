from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from mesl_finance.assets.domain.asset import AssetMode, AssetOwner
from mesl_finance.assets.domain.asset_event import AcquireSource, AssetEventKind


class AssetOut(BaseModel):
    id: int
    name: str
    mode: str
    ownership: str
    tag: str | None
    note: str


class CreateAssetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    mode: AssetMode
    ownership: AssetOwner
    tag: str | None = None
    note: str = ""


class EditAssetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    tag: str | None = None
    note: str | None = None
    mode: AssetMode | None = None
    ownership: AssetOwner | None = None


class AssetEventOut(BaseModel):
    """The event as stored; `ledger_transaction_id` names the expense that
    paid for a `purchase` (issue #10)."""

    id: int
    asset_id: int
    kind: str
    quantity: int
    occurred_on: date
    note: str
    ledger_transaction_id: int | None


class AssetEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: AssetEventKind
    quantity: int = Field(strict=True)
    occurred_on: date
    member_id: int | None = None
    source: AcquireSource | None = None
    ledger_transaction_id: int | None = None
    note: str = ""


class FixEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantity: int = Field(strict=True)
    occurred_on: date
    note: str = ""


class FixEventOut(BaseModel):
    id: int
    asset_id: int
    kind: str
    quantity: int
    occurred_on: date
    note: str
    reversal_id: int
    ledger_transaction_id: int | None


class AssetStateOut(BaseModel):
    asset_id: int
    asset_name: str
    ownership: str
    mode: str
    tag: str | None
    stock: int
    damaged: int
    with_members: int
    lost: int
    scrapped: int
    exchanged: int


class WhoHasWhatOut(BaseModel):
    asset_id: int
    asset_name: str
    member_id: int
    member_name: str
    quantity: int


class AssetActivityOut(BaseModel):
    asset_name: str
    ownership: str
    kind: str
    source: str | None
    units: int
    events: int
