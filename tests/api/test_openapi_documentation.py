"""Issue #12: the generated OpenAPI document must be self-explanatory.

The issue: 53 operations / 74 schemas ship with no summaries, no descriptions,
no field meanings and no error bodies, so only the designer can use the API
("no endpoint has any kind of documentation"). The approved triage outcome:
docs live in docstrings/comments only and surface through the generated
`docs/openapi.json` — ReDoc (`/redoc`) for reading, Swagger (`/docs`) for
trying things out; no second hand-written doc source (D-096 stands). Locked
brief answers: Q1=a exact error codes per op; Q2=a our problem-JSON 422 (the
fabricated `HTTPValidationError` disappears); Q3=a /health documents 200+503;
Q4=a short imperative summaries; Q5=a+b plain-English text with internal
references; Q6/a short for now (elaboration backlog: issue #13).

These tests pin the DOCUMENT `create_app(<schema-only settings>).openapi()`
produces; /code delivers docstrings, `Field(description=...)`,
`FastAPI(description=..., openapi_tags=...)` and per-op `responses=`, then
regenerates `docs/openapi.json` (D-162).

Library facts verified in installed source this session:
- a handler docstring becomes the operation description
  (fastapi/routing.py:1085);
- passing `responses={"422": ...}` suppresses FastAPI's auto
  `HTTPValidationError`, which it only adds when 422/4XX/default are all
  absent (fastapi/openapi/utils.py:517-521);
- `openapi_tags` / `description` are FastAPI/applications.py parameters
  (:245, :445-452);
- pydantic 2.14.1 emits `Field(description=...)` into the JSON schema
  properties (live probe this session);
- the wire error body is RFC 9457 problem+json `{type, title, status,
  detail, code}` plus `errors` on 422 (shared/api/problems.py:39-51,71-80).

EXPECTED_ERRORS below is the per-op exact 4xx table, derived from the
approved API tests this session:
- 401 on every op except /auth/login (D-158 Q2=a: the bearer JWT is required
  like every other read; every op but login sits behind `current_actor`);
- 404 only where the approved tests pin an adapter pre-check (members D-101
  Q3=a, envelopes D-066 Q5=a, cost centers D-070/D-122, assets D-129 Q6=a /
  D-133 Q4=a, snapshots D-154 Q4=a);
- 409 exactly where a pinned test asserts it (writes reaching PostgreSQL's
  rules, the fix endpoints, allocate, sweep, close tenure, health's tamper is
  503 not 409);
- 422 whenever the op has an inbound validation perimeter (a pydantic body or
  typed path/query parameters) — the pinned `validation_error` /
  `validation_failed` / `unknown_reference` tests cover most ops; the
  remaining ones are structurally guaranteed by the approved routes (bad body
  or non-numeric/non-date perimeter value -> the RequestValidationError
  handler, D-130/D-160: problems.py:71-80).
The rejections under 409/404 use different `code` values per op, so the
document pins the CODES (state), not the code strings; a response documented
here must mirror the wire media type `application/problem+json` (D-013), not
plain `application/json`.
"""

from __future__ import annotations

from typing import Any

from mesl_finance.main import create_app
from tests.api.test_export_openapi import EXPECTED_OPERATIONS, schema_only_settings

# (method, path) -> the 4xx problem-JSON status codes the operation can answer.
# Every entry cites its derivation in the module docstring above; the
# meta-test below fails the project the moment the table goes stale.
EXPECTED_ERRORS: dict[tuple[str, str], list[int]] = {
    ("POST", "/api/v1/auth/login"): [401, 422],
    ("GET", "/api/v1/health"): [401],
    ("GET", "/api/v1/entries"): [401, 422],
    ("POST", "/api/v1/deposits"): [401, 409, 422],
    ("POST", "/api/v1/expenses"): [401, 409, 422],
    ("POST", "/api/v1/refunds"): [401, 409, 422],
    ("POST", "/api/v1/transfers"): [401, 409, 422],
    ("POST", "/api/v1/entries/{entry_id}/fix-amount"): [401, 409, 422],
    ("POST", "/api/v1/entries/{entry_id}/edit-labels"): [401, 409, 422],
    ("POST", "/api/v1/envelopes"): [401, 409, 422],
    ("GET", "/api/v1/envelopes"): [401],
    ("POST", "/api/v1/envelopes/{envelope_id}/rename"): [401, 404, 409, 422],
    ("POST", "/api/v1/envelopes/{envelope_id}/settings"): [401, 404, 409, 422],
    ("POST", "/api/v1/envelopes/{envelope_id}/deactivate"): [401, 404, 409],
    ("GET", "/api/v1/allocation-context"): [401],
    ("POST", "/api/v1/allocation-suggestion"): [401, 422],
    ("POST", "/api/v1/allocations"): [401, 409, 422],
    ("POST", "/api/v1/cost-centers"): [401, 409, 422],
    ("GET", "/api/v1/cost-centers"): [401],
    ("POST", "/api/v1/cost-centers/{cost_center_id}/rename"): [401, 404, 409, 422],
    ("POST", "/api/v1/cost-centers/{cost_center_id}/status"): [401, 404, 409, 422],
    ("GET", "/api/v1/cost-centers/{cost_center_id}/summary"): [401, 404],
    ("POST", "/api/v1/sweeps"): [401, 409, 422],
    ("POST", "/api/v1/members"): [401, 422],
    ("GET", "/api/v1/members"): [401],
    ("POST", "/api/v1/members/{member_id}/edit"): [401, 404, 422],
    ("POST", "/api/v1/members/{member_id}/periods/start"): [401, 404, 409, 422],
    ("POST", "/api/v1/members/{member_id}/periods/end"): [401, 404, 409, 422],
    ("GET", "/api/v1/members/{member_id}/periods"): [401, 404, 422],
    ("POST", "/api/v1/members/{member_id}/adjustments"): [401, 404, 409, 422],
    ("GET", "/api/v1/members/{member_id}/adjustments"): [401, 404],
    ("POST", "/api/v1/fee-rates"): [401, 409, 422],
    ("GET", "/api/v1/fee-rates"): [401],
    ("POST", "/api/v1/shutdown-weeks"): [401, 409, 422],
    ("GET", "/api/v1/shutdown-weeks"): [401],
    ("GET", "/api/v1/shutdown-weeks/state"): [401],
    ("GET", "/api/v1/dues"): [401],
    ("POST", "/api/v1/assets"): [401, 409, 422],
    ("GET", "/api/v1/assets"): [401],
    ("POST", "/api/v1/assets/{asset_id}/edit"): [401, 404, 409, 422],
    ("POST", "/api/v1/assets/{asset_id}/events"): [401, 404, 409, 422],
    ("POST", "/api/v1/assets/{asset_id}/events/{event_id}/fix"): [401, 404, 409, 422],
    ("GET", "/api/v1/assets/state"): [401],
    ("GET", "/api/v1/assets/holdings"): [401],
    ("GET", "/api/v1/assets/replacement-queue"): [401],
    ("GET", "/api/v1/assets/activity"): [401, 422],
    ("POST", "/api/v1/reconciliations"): [401, 409, 422],
    ("GET", "/api/v1/reconciliation-status"): [401],
    ("GET", "/api/v1/unverified-entries"): [401],
    ("GET", "/api/v1/difference-suspects"): [401, 422],
    ("POST", "/api/v1/tenures/close"): [401, 409, 422],
    ("GET", "/api/v1/tenures/{tenure_id}/member-snapshots"): [401, 404, 422],
    ("GET", "/api/v1/tenures/{tenure_id}/asset-snapshots"): [401, 404, 422],
    ("GET", "/api/v1/tenures/{tenure_id}/holding-snapshots"): [401, 404, 422],
}

TAG_NAMES = (
    "auth",
    "assets",
    "ledger",
    "envelopes",
    "cost-centers",
    "members",
    "fees",
    "health",
    "reconciliation",
    "tenures",
)


def _document() -> dict[str, Any]:
    return create_app(schema_only_settings()).openapi()


def _operations(document: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (method.upper(), path): operations[method.lower()]
        for path, operations in document["paths"].items()
        for method in operations
        if method.upper() != "PARAMETERS"
    }


def _resolved(doc: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    if "$ref" in schema:
        components = doc["components"]["schemas"]
        return components[schema["$ref"].rsplit("/", 1)[-1]]
    return schema


def test_the_error_table_covers_exactly_the_current_operations() -> None:
    """Each new route must join this table; a stale one is a silent doc gap."""
    table_keys = set(EXPECTED_ERRORS)
    route_keys = set(EXPECTED_OPERATIONS)

    assert table_keys == route_keys


def test_every_operation_has_summary_and_description() -> None:
    document = _document()
    operations = _operations(document)

    assert set(operations) == set(EXPECTED_OPERATIONS)
    for (method, path), operation in operations.items():
        assert operation.get("summary"), f"{method} {path} has no summary"
        assert operation.get("description"), f"{method} {path} has no description"


def test_every_schema_property_is_described() -> None:
    document = _document()
    components = document["components"]["schemas"]

    assert components
    documented = 0
    for name, schema in components.items():
        properties = schema.get("properties", {})
        if not properties:
            continue  # enum / plain-string schemas define no properties
        documented += 1
        for field, spec in properties.items():
            assert spec.get("description"), f"{name}.{field} is undocumented"

    assert documented > 0, "no component schema carries fields at all"


def test_every_operation_documents_its_real_error_responses() -> None:
    """4xx rows must be the wire problem-JSON shape, exact codes per op,
    and FastAPI's fabricated HTTPValidationError must be gone."""
    document = _document()
    operations = _operations(document)

    for (method, path), operation in operations.items():
        responses: dict[str, Any] = operation["responses"]
        expected = EXPECTED_ERRORS[(method, path)]
        documented_errors = sorted(
            int(code) for code in responses if code.isdigit() and int(code) >= 400
        )
        assert documented_errors == sorted(expected), f"{method} {path}: {documented_errors}"

        for code in expected:
            content: dict[str, Any] = responses[str(code)]["content"]
            assert set(content) == {"application/problem+json"}, f"{method} {path} {code}"
            schema = _resolved(document, content["application/problem+json"]["schema"])
            assert {"code", "detail"} <= set(schema.get("properties", {})), (
                f"{method} {path} {code} does not describe a problem body"
            )

    assert "HTTPValidationError" not in document["components"]["schemas"]
    for (method, path), operation in operations.items():
        for response in operation["responses"].values():
            for media in response.get("content", {}).values():
                ref = media["schema"].get("$ref", "")
                assert not ref.endswith("HTTPValidationError"), f"{method} {path}"


def test_document_carries_the_guide() -> None:
    document = _document()
    info = document["info"]

    assert len(info["description"]) > 300, "the app overview is missing or thin"
    assert "fix" in info["description"].lower()
    assert "immutab" in info["description"].lower()

    tags: dict[str, str] = {
        tag["name"]: tag.get("description", "") for tag in document.get("tags", [])
    }
    assert set(tags) == set(TAG_NAMES)
    for name, description in tags.items():
        assert description, f"tag {name} carries no workflow guide"

    # the purchase recipe lives where someone looking for it will read it
    assert "expense" in tags["assets"].lower()
    assert "ledger_transaction_id" in tags["assets"].lower()
