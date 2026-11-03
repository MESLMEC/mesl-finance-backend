from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class EnvelopeOut(BaseModel):
    id: int = Field(description="The envelope")
    name: str = Field(description="Shown in the allocation screen and everywhere")
    target_cap: int | None = Field(
        description="Whole BDT the committee aims to keep here (None = uncapped)"
    )
    alloc_priority: int | None = Field(
        description="Order in which the allocation fills its gap (None = no slot)"
    )
    is_pool: bool = Field(description="True for 'Unallocated General' — the only true pool")
    active: bool = Field(description="False once retired; retired envelopes show in lists")


class CreateEnvelopeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Blank refused (422); unique over all envelopes (409)")
    target_cap: int | None = Field(
        default=None, description="Optional whole BDT; negative hits the CHECK"
    )
    alloc_priority: int | None = Field(default=None, description="Optional allocation order")


class RenameEnvelopeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="The new label; blank refused")


class EnvelopeSettingsRequest(BaseModel):
    """Both values are required and nullable: the body replaces the pair."""

    model_config = ConfigDict(extra="forbid")

    target_cap: int | None = Field(description="Whole BDT or null to clear")
    alloc_priority: int | None = Field(description="Whole number or null to clear")


class AllocationContextOut(BaseModel):
    pool_balance: int = Field(description="The pool's ledger balance (open tenure)")
    member_credit_held: int = Field(
        description="Credit members hold in advance (only positive member balances)"
    )
    pool_after_member_credit: int = Field(
        description="What the committee can actually allocate today"
    )


class AllocationSuggestionRequest(BaseModel):
    """The draft: whole taka to split, plus optional share weights per envelope."""

    model_config = ConfigDict(extra="forbid")

    amount: int = Field(strict=True, description="Whole BDT; positives only (<=0 → 422)")
    shares: dict[str, Annotated[int, Field(strict=True)]] | None = Field(
        default=None,
        description='`{"<envelope_id>": share}`; omit to reuse the last allocation\'s proportions',
    )


class AllocationSuggestionOut(BaseModel):
    envelope_id: int = Field(description="The envelope")
    envelope_name: str = Field(description="Shown on the screen")
    balance: int = Field(description="What the envelope currently holds")
    target_cap: int | None = Field(description="Its cap, if the committee set one")
    alloc_priority: int | None = Field(description="Its fill order, if set")
    gap: int | None = Field(description="How much more the cap needs, if capped")
    phase: str = Field(description="cap_fill | share | none — how this row got its amount")
    suggested: int = Field(description="The proposed split for this envelope")


class ConfirmAllocationRequest(BaseModel):
    """The confirmed split: whole taka per envelope id, plus the transfer's labels."""

    model_config = ConfigDict(extra="forbid")

    occurred_on: date = Field(description="The day of the split; within the open tenure")
    note: str = Field(description="REQUIRED, non-blank, worth keeping")
    amounts: dict[str, Annotated[int, Field(strict=True)]] = Field(
        description='`{"<envelope_id>": whole BDT}`; every value positive; keys are ids'
    )


class AllocationConfirmedOut(BaseModel):
    id: int = Field(description="The transfer's ledger entry")
    kind: str = Field(description="Always 'transfer'")
    pool_balance: int = Field(description="The pool's balance after the allocation")
