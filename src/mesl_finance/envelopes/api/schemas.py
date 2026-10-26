from pydantic import BaseModel, ConfigDict


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
