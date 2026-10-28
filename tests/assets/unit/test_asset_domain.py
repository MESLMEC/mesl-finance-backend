"""Domain tests for the asset record value object (roadmap step 9.1).

Approved brief answers this session: Q1=a the step carries asset records
(create + edit) and all nine event kinds; Q2=a a plain `GET /api/v1/assets`
list; Q5=a the app refuses the kind-shape violations as 422
`validation_failed` before SQL; Q6=a an unknown asset in the URL is 404
`not_found` naming the id; Q8=a the event response is
`{"id","asset_id","kind","quantity","occurred_on","note"}`; Q9=a
`ledger_transaction_id` is an optional body field on `acquired`.

What these tests pin (the domain API /code must provide):
- `AssetMode`: the two members of `asset_mode` (db/schema.sql:639)
- `AssetOwner`: the two members of `asset_owner` (db/schema.sql:640)
- `Asset.create(name=..., mode=..., ownership=..., tag=None, note="")`:
  keeps its fields; `mode`/`ownership` are plain strings here (the API layer
  validates them against the enums), and a blank name is refused with
  `ValidationFailed` - the D-070 Q4 / D-101 Q6=b app-side pattern, with the
  column CHECK at db/schema.sql:644 as the backstop.

Not tested here, on purpose: the case-insensitive tag uniqueness lives in the
partial unique index `assets_tag_unique` (db/schema.sql:651) and the
mode/ownership immutability once events exist in `asset_guard`
(db/schema.sql:716-724); both are pinned by the API tests.

The module is imported lazily (D-069): ruff classifies an import of a module
that does not exist yet as third-party, and the lazy import keeps each test's
failure individual instead of one collection error for the whole file.
"""

from importlib import import_module
from types import ModuleType
from typing import Any

import pytest

from mesl_finance.shared.errors import ValidationFailed

MODE_MEMBERS = [("INDIVIDUAL", "individual"), ("COUNTED", "counted")]
OWNER_MEMBERS = [("LAB", "lab"), ("ADMIN", "admin")]


def _module() -> ModuleType:
    try:
        return import_module("mesl_finance.assets.domain.asset")
    except ModuleNotFoundError:
        pytest.fail("src/mesl_finance/assets/domain/asset.py does not exist yet")


def _asset_class() -> Any:
    return vars(_module())["Asset"]


def _mode() -> Any:
    return vars(_module())["AssetMode"]


def _owner() -> Any:
    return vars(_module())["AssetOwner"]


def test_asset_modes_match_the_schema_enum() -> None:
    assert [(member.name, member.value) for member in _mode()] == MODE_MEMBERS


def test_asset_owners_match_the_schema_enum() -> None:
    assert [(member.name, member.value) for member in _owner()] == OWNER_MEMBERS


def test_an_asset_keeps_its_fields() -> None:
    thing = _asset_class().create(
        name="Oscilloscope",
        mode="individual",
        ownership="admin",
        tag="ADM-001",
        note="main bench",
    )

    assert (thing.name, thing.mode, thing.ownership, thing.tag, thing.note) == (
        "Oscilloscope",
        "individual",
        "admin",
        "ADM-001",
        "main bench",
    )


def test_tag_and_note_default_to_empty() -> None:
    thing = _asset_class().create(name="ESP32 DevKit", mode="counted", ownership="lab")

    assert (thing.tag, thing.note) == (None, "")


@pytest.mark.parametrize("name", ["", "   ", "\t\n "])
def test_a_blank_name_is_refused(name: str) -> None:
    with pytest.raises(ValidationFailed, match="name"):
        _asset_class().create(name=name, mode="counted", ownership="lab")
