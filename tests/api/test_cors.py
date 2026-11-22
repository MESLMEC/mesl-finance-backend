"""Issue (Q-004): CORS for the separate frontend host.

Approved brief (triage ACCEPT, user: "as per your suggestions"): origins from the new
`Settings.cors_origins` (empty default = current behaviour, no wildcard), bearer-only
(allow_credentials=False), allow_methods ["GET", "POST"] (Q4=a).

The approved tests use NO database: preflights are answered by the middleware before
routing (starlette/middleware/cors.py:86) and the simple requests below fail at 401
before any use case runs, exactly like the create_app probe of the triage session.

Verified in installed source before writing (AGENTS.md section 3):
- starlette 1.9.0 CORSMiddleware: a preflight (Origin + OPTIONS +
  Access-Control-Request-Method) is answered by the middleware itself (cors.py:86-89)
  with 200 "OK" for an allowed origin, Access-Control-Allow-Origin echoed to the
  requested origin (:111-115), Access-Control-Allow-Methods joined from allow_methods
  (:54) and Access-Control-Allow-Headers from SAFELISTED + allow_headers (:58,
  SAFELISTED = Accept/Accept-Language/Content-Language/Content-Type :12). A simple
  response echoes Access-Control-Allow-Origin only for allowed origins (:167-168);
  a disallowed origin gets none (:170). FastAPI re-exports it
  (fastapi/middleware/cors.py:1).
- pydantic-settings 2.16.0: a `list[str]` field is complex (sources/utils.py:204-210)
  and its env value is parsed with json.loads (sources/base.py:212) -> MESL_CORS_ORIGINS
  carries a JSON list.
"""

from fastapi.testclient import TestClient
from pydantic import SecretStr

from mesl_finance.main import create_app
from mesl_finance.shared.settings import Settings

ALLOWED = "http://localhost:5173"
DISALLOWED = "http://evil.example"

ALLOW_METHODS = ["GET", "POST"]  # approved brief Q4=a: the API's whole surface


def settings_with(origins: list[str] | None = None) -> Settings:
    """Settings good enough to construct the app; no connection is ever opened."""
    return Settings(
        database_url="postgresql+asyncpg://labapp:change-me@localhost:5432/mesl",
        admin_database_url=SecretStr("postgresql://postgres:change-me@localhost:5432/mesl"),
        jwt_secret=SecretStr("cors-tests-" + "x" * 32),
        auth_username="treasurer",
        auth_password_hash=SecretStr("$argon2id$v=19$m=8,t=1,p=1$c2FsdA$aGFzaA"),
        cors_origins=origins or [],
        _env_file=None,  # pyright: ignore[reportCallIssue]
    )


def test_preflight_from_an_allowed_origin_is_answered() -> None:
    """OPTIONS with Origin + request-method from a configured origin is answered 200 with
    the origin echoed, the approved methods and the requested headers allowed."""
    client = TestClient(create_app(settings_with([ALLOWED])))

    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": ALLOWED,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization, content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED
    assert response.headers["access-control-allow-methods"] == ", ".join(ALLOW_METHODS)
    requested_allowed = response.headers["access-control-allow-headers"].lower()
    assert "authorization" in requested_allowed
    assert "content-type" in requested_allowed


def test_a_simple_get_from_an_allowed_origin_carries_the_header() -> None:
    """GET with an allowed Origin carries access-control-allow-origin; the 401
    problem-JSON body itself is unchanged."""
    client = TestClient(create_app(settings_with([ALLOWED])))

    response = client.get("/api/v1/health", headers={"Origin": ALLOWED})

    assert response.status_code == 401
    assert response.headers["access-control-allow-origin"] == ALLOWED


def test_an_origin_not_on_the_list_gets_no_header() -> None:
    """A disallowed Origin gets no access-control-allow-origin header — the browser
    blocks the response, exactly as before this step."""
    client = TestClient(create_app(settings_with([ALLOWED])))

    response = client.get("/api/v1/health", headers={"Origin": DISALLOWED})

    assert response.status_code == 401
    assert "access-control-allow-origin" not in response.headers


def test_the_default_settings_emit_no_cors_headers() -> None:
    """Default Settings (no MESL_CORS_ORIGINS) must behave exactly as today: no
    access-control-allow-origin on any response."""
    client = TestClient(create_app(settings_with()))  # cors_origins default []

    response = client.get("/api/v1/health", headers={"Origin": DISALLOWED})

    assert "access-control-allow-origin" not in response.headers


def test_preflight_needs_no_bearer_token() -> None:
    """A preflight is answered without an Authorization header: the middleware answers
    before routing, so it is 200, not the 401 a route would give."""
    client = TestClient(create_app(settings_with([ALLOWED])))

    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": ALLOWED,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization",
        },
    )

    assert response.status_code == 200


def test_preflight_allows_the_idempotency_key_header() -> None:
    """Issue #4: the browser must be allowed to send `Idempotency-Key`.

    The header is NOT on the CORS safelist, so without it in `allow_headers` the
    preflight fails with 400 "Disallowed CORS headers" and the browser never
    sends the write (starlette/middleware/cors.py:127-131). The middleware
    answers the preflight itself, so no database and no token are needed.
    """
    client = TestClient(create_app(settings_with([ALLOWED])))

    response = client.options(
        "/api/v1/deposits",
        headers={
            "Origin": ALLOWED,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization, content-type, idempotency-key",
        },
    )

    assert response.status_code == 200
    allowed = response.headers["access-control-allow-headers"].lower()
    assert "idempotency-key" in allowed
    assert "authorization" in allowed
