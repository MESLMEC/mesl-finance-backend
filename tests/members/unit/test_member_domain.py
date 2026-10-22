"""Domain tests for the member and membership-period value objects (roadmap step 7.1).

Approved brief answers this session: Q6=b - a blank member name is refused by
the APP with 422 `validation_failed` (like cost centers), although
`db/schema.sql:89` also carries `CHECK (length(btrim(name)) > 0)`. Every other
question took the brief's labelled suggestion: Q1=a member edit is part of the
step, Q2=a the period read is part of it, Q3=a an unknown member addressed in
the URL is 404 `not_found`, Q4=a ending with nothing open is 404, Q5=a the end
action picks the single open period, Q7=a `MemberOut` is `{id,name,batch,note}`,
Q8=a the routes listed in tests/members/api/, Q9=a the shared translator gains
one 23P01 rule, Q10=a a partial edit (explicit null clears `batch`), Q11=a
create takes `name` plus optional `batch`/`note`.

What these tests pin (the domain API /code must provide):
- `Member.create(*, name, batch=None, note="")` keeps exactly the entered values
  (`members` has no other editable labels, db/schema.sql:87-93)
- `Member.edit(*, fields, name=None, batch=None, note=None)` changes ONLY the
  fields named in `fields`, and refuses an edit that names none
- a whole-number id is required by `MembershipPeriod` (D-047 strictness)
- a new `MembershipPeriod(member_id=..., start_date=...)` has `end_date=None`

Not tested here, on purpose (AGENTS.md section 5): the date order
(`end_date >= start_date`, db/schema.sql:100), the no-overlap EXCLUDE
(:101-102) and every `period_guard` refusal (:193-218) are PostgreSQL's and are
pinned end to end in tests/members/api/test_membership_periods_api.py.

The module is imported lazily, like the envelope/cost-center/ledger domain
tests: ruff classifies an import of a module that does not exist yet as
third-party, so a module-level import would have to be re-sorted the moment
/code adds it (D-069). The lazy import also keeps each test's failure
individual ("module does not exist yet") instead of one collection error for
the whole file.

Library APIs verified in installed source this session (AGENTS.md section 3):
- `importlib.import_module` and `types.ModuleType` are stdlib;
- `pytest.raises` / `pytest.fail` / `pytest.mark.parametrize`
  (pytest 9.1.1, .venv/lib/python3.15/site-packages/_pytest/python.py:1231);
- `datetime.date` is stdlib; no third-party call is made by these tests.
"""

from datetime import date
from importlib import import_module
from types import ModuleType
from typing import Any

import pytest

from mesl_finance.shared.errors import ValidationFailed


def _member_module() -> ModuleType:
    try:
        return import_module("mesl_finance.members.domain.member")
    except ModuleNotFoundError:
        pytest.fail("src/mesl_finance/members/domain/member.py does not exist yet")


def _member_class() -> Any:
    return vars(_member_module())["Member"]


def _period_class() -> Any:
    return vars(_member_module())["MembershipPeriod"]


def test_create_keeps_name_batch_and_note() -> None:
    member = _member_class().create(name="Ayesha", batch="2024", note="lab member")

    assert (member.name, member.batch, member.note) == ("Ayesha", "2024", "lab member")


def test_defaults_are_no_batch_and_an_empty_note() -> None:
    """db/schema.sql:90-91: `batch` has no default (NULL), `note` defaults to ''."""
    member = _member_class().create(name="Ayesha")

    assert (member.batch, member.note) == (None, "")


def test_partial_edit_changes_only_supplied_fields() -> None:
    member = _member_class().create(name="Ayesha", batch="2024", note="joined")

    edited = member.edit(fields=frozenset({"batch"}), batch=None)

    assert (edited.name, edited.batch, edited.note) == ("Ayesha", None, "joined")


def test_edit_without_fields_is_refused() -> None:
    member = _member_class().create(name="Ayesha")

    with pytest.raises(ValidationFailed, match="field"):
        member.edit(fields=frozenset())


@pytest.mark.parametrize("member_id", ["1", 1.0, True])
def test_ids_must_be_whole_numbers(member_id: Any) -> None:
    """D-047 strictness: only a real `int` names a member (bool is refused)."""
    with pytest.raises(ValidationFailed, match="member"):
        _period_class()(member_id=member_id, start_date=date(2026, 2, 1))


def test_period_starts_open() -> None:
    period = _period_class()(member_id=1, start_date=date(2026, 2, 1))

    assert (period.member_id, period.start_date, period.end_date) == (
        1,
        date(2026, 2, 1),
        None,
    )
