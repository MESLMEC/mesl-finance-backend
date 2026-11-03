from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from mesl_finance.ledger.domain.entry import EntryKind, IncomeSource


class DepositRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: int = Field(strict=True, gt=0, description="Whole BDT, never a float")
    occurred_on: date = Field(
        description="The day the money was paid in; not before the tenure opened"
    )
    source: IncomeSource = Field(
        description="Where it came from: weekly_fee, registration, sponsorship,"
        " admin_grant, donation, other"
    )
    note: str = Field(default="", description="Say something worth reading later")
    tag: str | None = Field(default=None, description="Free label (e.g. 'fest gate')")
    cost_center_id: int | None = Field(
        default=None, description="Attach to an event/project when relevant"
    )
    member_id: int | None = Field(
        default=None,
        description="Required for weekly_fee, forbidden otherwise (the pool owns member money)",
    )
    envelope_id: int | None = Field(
        default=None,
        description="Default: the Unallocated General pool; naming another puts it there",
    )


class EntryCreated(BaseModel):
    id: int = Field(description="The new ledger entry")


class ExpenseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: int = Field(strict=True, gt=0, description="Whole BDT spent")
    occurred_on: date = Field(description="The day it was paid out; not before the tenure opened")
    envelope_id: int = Field(description="The envelope it comes from — the pool counts too")
    note: str = Field(default="", description="Why it went out (spend reasons differ)")
    tag: str | None = Field(default=None, description="Free label")
    cost_center_id: int | None = Field(
        default=None, description="Attach to an event/project so its summary tracks it"
    )


class ExpenseCreated(BaseModel):
    id: int = Field(description="The new ledger entry")
    kind: EntryKind = Field(description="Always 'expense'")
    balance: int = Field(description="The envelope's balance AFTER the write")


class RefundRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: int = Field(strict=True, gt=0, description="Whole BDT returned to the member")
    occurred_on: date = Field(description="The day it left the lab")
    note: str = Field(default="", description="Why the credit went back")
    tag: str | None = Field(default=None, description="Free label")
    member_id: int = Field(description="Who gets the money back")
    cost_center_id: int | None = Field(default=None, description="Only if it belongs to one")


class RefundCreated(BaseModel):
    id: int = Field(description="The new ledger entry (an expense on the pool)")
    kind: EntryKind = Field(description="Always 'expense'")
    balance: int = Field(description="The pool's balance AFTER the write")


class TransferRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: int = Field(strict=True, gt=0, description="Whole BDT moved")
    occurred_on: date = Field(description="The day of the move")
    from_envelope_id: int = Field(description="The envelope the money leaves")
    to_envelope_id: int = Field(description="The envelope the money enters; must differ")
    note: str = Field(description="REQUIRED non-blank: why the money moves")
    tag: str | None = Field(default=None, description="Free label")
    cost_center_id: int | None = Field(default=None, description="Only if it belongs to one")


class TransferCreated(BaseModel):
    id: int = Field(description="The new ledger entry")
    kind: EntryKind = Field(description="Always 'transfer'")
    from_balance: int = Field(description="The source envelope's balance after the write")
    to_balance: int = Field(description="The target envelope's balance after the write")


class FixAmountRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: int = Field(strict=True, gt=0, description="Whole BDT: the CORRECTED amount")
    occurred_on: date = Field(
        description="Written on both the reversal and the replacement (no date is inherited)"
    )
    note: str = Field(description="The REQUIRED reason for the fix")


class FixAmountCreated(BaseModel):
    id: int = Field(description="The replacement entry")
    kind: EntryKind = Field(description="The original's kind")
    reversal_id: int = Field(description="The mirror entry that voids the original")
    corrected_from: int = Field(description="The original entry id")
    balance: int = Field(description="The envelope's balance after the correction")


class LabelEditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str | None = Field(
        default=None,
        description="Omit = unchanged; never null; blank on transfer/sweep/reversal refused",
    )
    tag: str | None = Field(default=None, description="Omit = unchanged; explicit null clears")
    cost_center_id: int | None = Field(
        default=None,
        strict=True,
        description="Omit = unchanged; explicit null clears; unknown ids refused",
    )
    occurred_on: date | None = Field(
        default=None, description="Omit = unchanged; never null on write; within the tenure"
    )
    source: IncomeSource | None = Field(
        default=None, description="Omit = unchanged; explicit null clears; only deposits carry one"
    )


class EntryLabelsOut(BaseModel):
    id: int = Field(description="The entry")
    kind: EntryKind = Field(description="The entry's kind")
    note: str = Field(description="The current note")
    tag: str | None = Field(description="The current tag label")
    cost_center_id: int | None = Field(description="The currently attached cost center (if any)")
    occurred_on: date = Field(description="The business date")
    source: IncomeSource | None = Field(description="Deposits only: where it came from")


class EntryOut(BaseModel):
    id: int = Field(description="The entry")
    tenure_id: int = Field(description="The tenure recorded into")
    kind: EntryKind = Field(description="The entry's kind")
    occurred_on: date = Field(description="The business date (as recorded)")
    recorded_at: datetime = Field(description="When it was recorded")
    recorded_by: str = Field(description="Investing treasurer — the JWT subject")
    note: str = Field(description="The current note")
    tag: str | None = Field(description="The current tag label")
    cost_center_id: int | None = Field(description="The attached cost center if any")
    member_id: int | None = Field(description="Set for weekly fee payments and refunds")
    source: IncomeSource | None = Field(description="Deposits only")
    corrected_from: int | None = Field(
        description="Set on a FIX: the ORIGINAL wrong entry this one replaces"
    )
