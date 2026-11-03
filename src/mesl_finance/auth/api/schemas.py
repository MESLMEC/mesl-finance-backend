from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(description="The treasurer's username (server settings, D-006)")
    password: str = Field(description="The treasurer's password (checked against the argon2 hash)")


class TokenResponse(BaseModel):
    access_token: str = Field(description="The bearer JWT; send `Authorization: Bearer <token>`")
    token_type: str = Field(default="bearer", description="Always 'bearer'")
    expires_at: datetime = Field(description="When the token stops being accepted (72 h, D-006)")
