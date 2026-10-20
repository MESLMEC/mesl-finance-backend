"""Domain errors. Pure Python: no HTTP, no database. The API layer decides status codes."""


class DomainError(Exception):
    code = "domain_error"
    title = "Domain error"

    def __init__(self, detail: str = "") -> None:
        super().__init__(detail or self.title)
        self.detail = detail or self.title


class ValidationFailed(DomainError):
    code = "validation_failed"
    title = "Validation failed"


class UnknownReference(DomainError):
    code = "unknown_reference"
    title = "Unknown reference"


class RuleViolation(DomainError):
    code = "rule_violation"
    title = "A lab rule refused this change"


class NoOpenTenure(RuleViolation):
    code = "no_open_tenure"
    title = "There is no open tenure"


class DateBeforeTenure(RuleViolation):
    code = "date_before_tenure"
    title = "Date is before the tenure opened"


class Unique(RuleViolation):
    code = "unique"
    title = "Already exists"


class Unauthorized(DomainError):
    code = "unauthorized"
    title = "Authentication required"


class InvalidCredentials(Unauthorized):
    code = "invalid_credentials"
    title = "Wrong username or password"


class InvalidToken(Unauthorized):
    code = "invalid_token"
    title = "Missing, expired or invalid token"
