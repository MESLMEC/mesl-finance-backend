from typing import Annotated, cast

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from mesl_finance.auth.application.login import Login
from mesl_finance.auth.application.ports import TokenVerifier
from mesl_finance.shared.errors import InvalidToken

_bearer = HTTPBearer(auto_error=False)


def get_login(request: Request) -> Login:
    return cast(Login, request.app.state.login)


def current_user(
    request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]
) -> str:
    """The authenticated username (the JWT subject); it becomes `recorded_by` and `app.actor`."""
    if credentials is None:
        raise InvalidToken
    verifier = cast(TokenVerifier, request.app.state.token_service)
    return verifier.verify(credentials.credentials)
