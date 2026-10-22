from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from mesl_finance.ledger.domain.entry import EntryKind, IncomeSource


class DepositRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: int = Field(strict=True, gt=0, description="Whole BDT")
    occurred_on: date
    source: IncomeSource
    note: str = ""
    tag: str | None = None
    cost_center_id: int | None = None
    member_id: int | None = Field(
        default=None, description="Required for weekly_fee, forbidden otherwise"
    )
    envelope_id: int | None = Field(
        default=None, description="Default: the Unallocated General pool"
    )


class EntryCreated(BaseModel):
    id: int


class ExpenseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: int = Field(strict=True, gt=0, description="Whole BDT spent")
    occurred_on: date
    envelope_id: int = Field(description="The envelope the money is spent from")
    note: str = ""
    tag: str | None = None
    cost_center_id: int | None = None


class ExpenseCreated(BaseModel):
    id: int
    kind: EntryKind
    balance: int


class TransferRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: int = Field(strict=True, gt=0, description="Whole BDT moved")
    occurred_on: date
    from_envelope_id: int = Field(description="The envelope the money leaves")
    to_envelope_id: int = Field(description="The envelope the money enters")
    note: str = Field(description="Why the money moves")
    tag: str | None = None
    cost_center_id: int | None = None


class TransferCreated(BaseModel):
    id: int
    kind: EntryKind
    from_balance: int
    to_balance: int


class FixAmountRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: int = Field(strict=True, gt=0, description="Whole BDT: the corrected amount")
    occurred_on: date = Field(description="Written on BOTH the reversal and the replacement")
    note: str = Field(description="Why the amount is corrected")


class FixAmountCreated(BaseModel):
    id: int
    kind: EntryKind
    reversal_id: int
    corrected_from: int
    balance: int


class LabelEditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str | None = None
    tag: str | None = None
    cost_center_id: int | None = Field(default=None, strict=True)
    occurred_on: date | None = None
    source: IncomeSource | None = None


class EntryLabelsOut(BaseModel):
    id: int
    kind: EntryKind
    note: str
    tag: str | None
    cost_center_id: int | None
    occurred_on: date
    source: IncomeSource | None


class EntryOut(BaseModel):
    id: int
    tenure_id: int
    kind: EntryKind
    occurred_on: date
    recorded_at: datetime
    recorded_by: str
    note: str
    tag: str | None
    cost_center_id: int | None
    member_id: int | None
    source: IncomeSource | None
    corrected_from: int | None
