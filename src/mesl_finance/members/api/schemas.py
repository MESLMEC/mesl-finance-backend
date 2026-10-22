from datetime import date

from pydantic import BaseModel, ConfigDict


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
