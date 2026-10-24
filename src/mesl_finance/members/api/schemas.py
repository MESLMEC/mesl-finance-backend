from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from mesl_finance.members.domain.adjustment import AdjustmentKind


class MemberOut(BaseModel):
    id: int
    name: str
    batch: str | None
    note: str


class CreateMemberRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    batch: str | None = None
    note: str = ""


class EditMemberRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    batch: str | None = None
    note: str | None = None


class MembershipPeriodOut(BaseModel):
    id: int
    member_id: int
    start_date: date
    end_date: date | None


class StartPeriodRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_date: date


class EndPeriodRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    end_date: date


class AdjustmentOut(BaseModel):
    id: int
    member_id: int
    kind: str
    amount: int
    occurred_on: date
    note: str
    recorded_at: datetime
    recorded_by: str


class CreateAdjustmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: AdjustmentKind
    amount: int = Field(strict=True, description="Signed whole BDT; positive adds credit")
    occurred_on: date
    note: str = ""
