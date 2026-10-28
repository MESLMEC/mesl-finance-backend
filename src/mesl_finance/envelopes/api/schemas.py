from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class EnvelopeOut(BaseModel):
    id: int
    name: str
    target_cap: int | None
    alloc_priority: int | None
    is_pool: bool
    active: bool


class CreateEnvelopeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    target_cap: int | None = None
    alloc_priority: int | None = None


class RenameEnvelopeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str


class EnvelopeSettingsRequest(BaseModel):
    """Both values are required and nullable: the body replaces the pair."""

    model_config = ConfigDict(extra="forbid")

    target_cap: int | None
    alloc_priority: int | None


class AllocationContextOut(BaseModel):
    pool_balance: int
    member_credit_held: int
    pool_after_member_credit: int


class AllocationSuggestionRequest(BaseModel):
    """The draft: whole taka to split, plus optional share weights per envelope."""

    model_config = ConfigDict(extra="forbid")

    amount: int = Field(strict=True, description="Whole BDT to split")
    shares: dict[str, Annotated[int, Field(strict=True)]] | None = Field(
        default=None, description='Optional {"<envelope_id>": share} weights'
    )


class AllocationSuggestionOut(BaseModel):
    envelope_id: int
    envelope_name: str
    balance: int
    target_cap: int | None
    alloc_priority: int | None
    gap: int | None
    phase: str
    suggested: int
