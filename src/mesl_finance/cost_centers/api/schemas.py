from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from mesl_finance.ledger.domain.entry import EntryKind


class CostCenterOut(BaseModel):
    id: int = Field(description="The cost center")
    name: str = Field(description="The label; unique per kind")
    kind: str = Field(description="event | member_project | lab_project | competition")
    status: str = Field(description="planned | active | completed | cancelled")


class CreateCostCenterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Blank refused app-side (422)")
    kind: str = Field(description="The four kinds; unknown ones → 409 rule_violation")


class RenameCostCenterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Blank refused")


class SetCostCenterStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(description="Any of the four allowed values, any time")


class CostCenterSummaryOut(BaseModel):
    cost_center_id: int = Field(description="The cost center")
    name: str = Field(description="Shown in the report")
    kind: str = Field(description="Its kind")
    status: str = Field(description="Its status")
    money_in: int = Field(description="Deposits tagged with it (reversals counted correctly)")
    money_out: int = Field(description="Expenses tagged with it")
    swept: int = Field(description="What already went back to the pool")
    leftover: int = Field(description="in - out - swept (0 without entries)")


class SweepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cost_center_id: int = Field(strict=True, description="The event/project whose leftover moves")
    from_envelope_id: int = Field(strict=True, description="The envelope holding it (NOT the pool)")
    occurred_on: date = Field(description="The day it moved; within the open tenure")
    note: str = Field(description="REQUIRED, non-blank")


class SweepCreated(BaseModel):
    id: int = Field(description="The sweep's ledger entry")
    kind: EntryKind = Field(description="Always 'sweep'")
    from_balance: int = Field(description="The envelope's balance after the sweep")
    pool_balance: int = Field(description="The pool's balance after the sweep")
