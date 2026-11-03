from typing import Annotated

from fastapi import APIRouter, Depends

from mesl_finance.auth.api.dependencies import get_login
from mesl_finance.auth.api.schemas import LoginRequest, TokenResponse
from mesl_finance.auth.application.login import Login
from mesl_finance.shared.api.responses import problem_responses

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", summary="Log in", responses={**problem_responses(401, 422)})
def login(body: LoginRequest, use_case: Annotated[Login, Depends(get_login)]) -> TokenResponse:
    """Trade the treasurer's username and password for a bearer JWT.

    Returns `{access_token, token_type: "bearer", expires_at}`; the token is
    accepted by every other route (D-006: one treasurer, hash from settings,
    72-hour validity). Wrong username or password answers 401
    `invalid_credentials` (application/problem+json); there is one login and
    no admin reset endpoint.
    """
    token = use_case(body.username, body.password)
    return TokenResponse(access_token=token.token, expires_at=token.expires_at)
