from datetime import date

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
