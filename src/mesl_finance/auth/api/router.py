from typing import Annotated

from fastapi import APIRouter, Depends

from mesl_finance.auth.api.dependencies import get_login
from mesl_finance.auth.api.schemas import LoginRequest, TokenResponse
from mesl_finance.auth.application.login import Login

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(body: LoginRequest, use_case: Annotated[Login, Depends(get_login)]) -> TokenResponse:
    token = use_case(body.username, body.password)
    return TokenResponse(access_token=token.token, expires_at=token.expires_at)
