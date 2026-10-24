"""Domain tests for member adjustments (roadmap step 7.3).

Approved brief this session: every question took the brief's labelled suggestion
(same pattern as D-101/D-104): Q3=a the amount is SIGNED and the direction rules
stay in PostgreSQL; Q4=c the app refuses a blank note for `waiver`/`correction`
as 422 `validation_failed` while the kind-specific SIGNS stay the table CHECKs'
(409 `rule_violation`); Q9=a one new module
`src/mesl_finance/members/domain/adjustment.py` with `AdjustmentKind`,
`MemberAdjustment` and `AdjustmentView`.

What these tests pin (the domain API /code must provide):
- `AdjustmentKind`: the four members, name and value, of `adjustment_kind`
  (db/schema.sql:128), in the schema's order.
- `MemberAdjustment(member_id=..., kind=..., amount=..., occurred_on=..., note=...)`:
  an immutable value object whose `note` defaults to `""`.
- `MemberAdjustment` refuses a non-`int` amount or member id with
  `ValidationFailed` (the D-047 strictness: `bool`, `float`, `str`, `None`).
- `MemberAdjustment` refuses a blank note when the kind requires one:
  `waiver` and `correction` (db/schema.sql:140). `credit_donation` and `opening`
  accept a blank note.

Not tested here, on purpose: `amount <> 0` (db/schema.sql:133), the kind-specific
signs (`waiver > 0`, `credit_donation < 0`, db/schema.sql:138-139) and the
closed-tenure date rule (`adj_guard`, db/schema.sql:185-191) are PostgreSQL's and
are never duplicated in Python (AGENTS.md section 5, Q4=c). The database side is
already pinned by the 7.0 port (`tests/db/test_fees.py`).

The module is imported lazily, like the ledger domain objects (D-069/D-078):
ruff classifies an import of a module that does not exist yet as third-party, so
a module-level import would have to be re-sorted the moment /code adds it. The
lazy import also keeps each test's failure individual ("module does not exist
yet") instead of one collection error for the whole file.
"""

from datetime import date
from importlib import import_module
from types import ModuleType
from typing import Any

import pytest

from mesl_finance.shared.errors import ValidationFailed

ADJUSTMENT_KIND_MEMBERS = [
    ("WAIVER", "waiver"),
    ("CREDIT_DONATION", "credit_donation"),
    ("OPENING", "opening"),
    ("CORRECTION", "correction"),
]

ADJUSTMENT_DATE = date(2026, 2, 1)


def _adjustment_module() -> ModuleType:
    try:
        return import_module("mesl_finance.members.domain.adjustment")
    except ModuleNotFoundError:
        pytest.fail("src/mesl_finance/members/domain/adjustment.py does not exist yet")


def _adjustment_kind() -> Any:
    return vars(_adjustment_module())["AdjustmentKind"]


def _member_adjustment_class() -> Any:
    return vars(_adjustment_module())["MemberAdjustment"]


def test_kinds_match_the_schema_enum() -> None:
    assert [(member.name, member.value) for member in _adjustment_kind()] == (
        ADJUSTMENT_KIND_MEMBERS
    )


def test_an_adjustment_keeps_its_values_and_defaults_the_note_to_empty() -> None:
    adjustment = _member_adjustment_class()(
        member_id=1,
        kind=_adjustment_kind().OPENING,
        amount=40,
        occurred_on=ADJUSTMENT_DATE,
    )

    assert (
        adjustment.member_id,
        adjustment.kind,
        adjustment.amount,
        adjustment.occurred_on,
        adjustment.note,
    ) == (1, _adjustment_kind().OPENING, 40, ADJUSTMENT_DATE, "")


@pytest.mark.parametrize("amount", [10.5, "20", True, None])
def test_a_non_whole_amount_is_refused(amount: Any) -> None:
    with pytest.raises(ValidationFailed):
        _member_adjustment_class()(
            member_id=1,
            kind=_adjustment_kind().WAIVER,
            amount=amount,
            occurred_on=ADJUSTMENT_DATE,
            note="forgiven",
        )


@pytest.mark.parametrize("member_id", ["1", True])
def test_a_non_integer_member_id_is_refused(member_id: Any) -> None:
    with pytest.raises(ValidationFailed):
        _member_adjustment_class()(
            member_id=member_id,
            kind=_adjustment_kind().WAIVER,
            amount=40,
            occurred_on=ADJUSTMENT_DATE,
            note="forgiven",
        )


@pytest.mark.parametrize("kind_name", ["WAIVER", "CORRECTION"])
def test_a_blank_note_is_refused_for_waiver_and_correction(kind_name: str) -> None:
    kind = getattr(_adjustment_kind(), kind_name)

    for blank in ("", "   "):
        with pytest.raises(ValidationFailed):
            _member_adjustment_class()(
                member_id=1,
                kind=kind,
                amount=40,
                occurred_on=ADJUSTMENT_DATE,
                note=blank,
            )


@pytest.mark.parametrize("kind_name", ["CREDIT_DONATION", "OPENING"])
def test_a_blank_note_is_allowed_for_credit_donation_and_opening(kind_name: str) -> None:
    adjustment = _member_adjustment_class()(
        member_id=1,
        kind=getattr(_adjustment_kind(), kind_name),
        amount=-40,
        occurred_on=ADJUSTMENT_DATE,
    )

    assert adjustment.note == ""
