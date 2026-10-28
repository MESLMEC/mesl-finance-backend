from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from mesl_finance.ledger.domain.entry import EntryKind


class CostCenterOut(BaseModel):
    id: int
    name: str
    kind: str
    status: str


class CreateCostCenterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    kind: str


class RenameCostCenterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str


class SetCostCenterStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str


class CostCenterSummaryOut(BaseModel):
    cost_center_id: int
    name: str
    kind: str
    status: str
    money_in: int
    money_out: int
    swept: int
    leftover: int


class SweepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cost_center_id: int = Field(strict=True, description="The event's cost center")
    from_envelope_id: int = Field(strict=True, description="The envelope holding the leftover")
    occurred_on: date
    note: str = Field(description="Why the leftover is swept")


class SweepCreated(BaseModel):
    id: int
    kind: EntryKind
    from_balance: int
    pool_balance: int
