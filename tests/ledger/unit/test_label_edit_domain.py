"""LabelEdit value object (ROADMAP 6.6, label edit).

Approved contract (step 6.6 brief): Q7 was answered b, every other question was
left unanswered, so the brief's labelled suggestions stand - Q2=a (any
non-opening entry may be relabelled; the database's ``tx_label_edit``,
db/schema.sql:376-410, owns the rest), Q3=a (partial edit; an explicit null
clears ``tag``/``cost_center_id``/``source``; ``note`` and ``occurred_on`` are
never null), Q4=a (an edit naming no field is refused), Q7=b (a blank note is
refused by the APP when the entry's kind needs one, db/schema.sql:259).

The domain judges only the request's own shape: the entry's tenure, the opening
wall and the kind shapes stay PostgreSQL's (AGENTS.md section 5). ``fields``
names what the request supplied, so a null value on a nullable field is a
deliberate clear and not "unchanged".
"""

from datetime import date
from importlib import import_module
from types import ModuleType
from typing import Any

import pytest

from mesl_finance.ledger.domain.entry import EntryKind, IncomeSource
from mesl_finance.shared.errors import ValidationFailed

DAY = date(2026, 10, 20)


def _module(name: str) -> ModuleType:
    try:
        return import_module(name)
    except ModuleNotFoundError:
        pytest.fail(f"{name} does not exist yet")


def _label_edit_class() -> Any:
    return vars(_module("mesl_finance.ledger.domain.label_edit"))["LabelEdit"]


def edit(**overrides: object) -> Any:
    fields: dict[str, object] = {
        "entry_id": 42,
        "fields": frozenset({"note"}),
        "note": "fees wk 27",
    }
    fields.update(overrides)
    return _label_edit_class().create(**fields)


def test_a_partial_edit_records_only_the_fields_it_names() -> None:
    label = edit()

    assert label.fields == frozenset({"note"})
    assert (
        label.entry_id,
        label.note,
        label.tag,
        label.cost_center_id,
        label.occurred_on,
        label.source,
    ) == (42, "fees wk 27", None, None, None, None)


def test_an_explicit_null_on_tag_or_cost_center_counts_as_supplied() -> None:
    label = edit(
        fields=frozenset({"tag", "cost_center_id"}),
        note=None,
        tag=None,
        cost_center_id=None,
    )

    assert label.fields == frozenset({"tag", "cost_center_id"})
    assert label.tag is None
    assert label.cost_center_id is None


def test_an_edit_with_no_fields_is_refused() -> None:
    with pytest.raises(ValidationFailed):
        edit(fields=frozenset[str](), note=None)


def test_an_unknown_field_name_is_refused() -> None:
    with pytest.raises(ValidationFailed):
        edit(fields=frozenset({"amount"}), note=None)


@pytest.mark.parametrize("kind", [EntryKind.TRANSFER, EntryKind.SWEEP, EntryKind.REVERSAL])
def test_a_blank_note_is_refused_for_a_kind_that_needs_one(kind: EntryKind) -> None:
    with pytest.raises(ValidationFailed):
        edit(note="   ").validate_for(kind)


@pytest.mark.parametrize("kind", [EntryKind.DEPOSIT, EntryKind.EXPENSE])
def test_a_blank_note_is_allowed_on_a_kind_that_does_not_need_one(kind: EntryKind) -> None:
    assert edit(note="   ").validate_for(kind) is None


@pytest.mark.parametrize("bad", [True, 1.5, "42"])
def test_a_non_whole_entry_id_is_refused(bad: object) -> None:
    with pytest.raises(ValidationFailed):
        edit(entry_id=bad)


def test_a_non_int_cost_center_is_refused() -> None:
    for bad in (True, "3", 1.5):
        with pytest.raises(ValidationFailed):
            edit(fields=frozenset({"cost_center_id"}), note=None, cost_center_id=bad)

    accepted = edit(fields=frozenset({"cost_center_id"}), note=None, cost_center_id=3)
    assert accepted.cost_center_id == 3


def test_source_must_be_an_income_source() -> None:
    with pytest.raises(ValidationFailed):
        edit(fields=frozenset({"source"}), note=None, source="other")

    accepted = edit(fields=frozenset({"source"}), note=None, source=IncomeSource.DONATION)
    assert accepted.source is IncomeSource.DONATION


def test_occurred_on_must_be_a_date() -> None:
    with pytest.raises(ValidationFailed):
        edit(fields=frozenset({"occurred_on"}), note=None, occurred_on="2026-10-20")

    accepted = edit(fields=frozenset({"occurred_on"}), note=None, occurred_on=DAY)
    assert accepted.occurred_on == DAY
