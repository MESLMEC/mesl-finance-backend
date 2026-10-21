from pydantic import BaseModel, ConfigDict


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
