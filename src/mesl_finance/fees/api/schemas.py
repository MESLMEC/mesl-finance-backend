from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class FeeRateOut(BaseModel):
    id: int
    effective_from: date
    amount: int
    recorded_at: datetime
    recorded_by: str


class CreateFeeRateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    effective_from: date
    amount: int = Field(strict=True, description="Whole BDT per member per week")


class ShutdownEventOut(BaseModel):
    id: int
    week_start: date
    is_shutdown: bool
    reason: str
    recorded_at: datetime
    recorded_by: str


class SetShutdownRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_week: date
    to_week: date
    is_shutdown: bool = True
    reason: str = ""


class ShutdownResult(BaseModel):
    weeks: int


class StandingOut(BaseModel):
    member_id: int
    member_name: str
    is_member_now: bool
    weeks_owed: int
    owed: int
    credits: int
    balance: int
    weeks_overdue: int
    oldest_unpaid_week: date | None
