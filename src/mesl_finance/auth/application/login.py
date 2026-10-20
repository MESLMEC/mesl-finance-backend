from mesl_finance.auth.application.ports import AccessToken, CredentialChecker, TokenIssuer
from mesl_finance.shared.errors import InvalidCredentials


class Login:
    def __init__(self, credentials: CredentialChecker, tokens: TokenIssuer) -> None:
        self._credentials = credentials
        self._tokens = tokens

    def __call__(self, username: str, password: str) -> AccessToken:
        if not self._credentials.verify(username, password):
            raise InvalidCredentials
        return self._tokens.issue(username)
