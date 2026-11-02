r"""Contract tests for assets: acquire, lend, damage, repair, exchange with admin,
count corrections, the admin report and the handover register.

Ported from the worked example `db/examples/05_assets.sql`. The behaviour already exists in
`db/schema.sql`, so every test here passes at once (TEST-ONLY step, D-045).

Tests referenced by the coverage table:

  T1  test_setup_replays_example_prefix
  T2  test_assets_are_created
  T3  test_acquisitions_succeed
  T4  test_lend_return_damage_repair_flow
  T5  test_expect_overview_after_first_cycle
  T6  test_exchange_replacement_lost_scrapped_correction
  T7  test_expect_overview_after_second_cycle
  T8  test_fix_mistaken_lend_reversal_plus_replacement
  T9  test_note_edit_is_logged
  T10 test_rejected_mistakes (16 parametrized cases)
  T11 test_asset_name_edit_is_allowed
  T12 test_asset_activity_numbers
  T13 test_the_database_stays_healthy
  T14 test_close_tenure_writes_the_handover_register
  T15 test_closed_tenure_touches_are_rejected (3 cases)
  T16 test_the_new_tenure_carries_on
  T17 test_the_database_is_healthy_after_close
  T18 test_superuser_tamper_is_detected

Issue #11 (migration 0002, `asset_purchase_needs_link`) adds three cases that are NOT
lines of the example - the rule is new, so the example cannot cover it:

  I1  test_a_purchase_must_name_its_payment
  I2  test_a_purchase_with_a_link_is_accepted
  I3  test_a_non_purchase_acquisition_needs_no_link

Coverage proof - every `EXPECT` / `EXPECT FAIL` line of the example, in script order. The file
header (line 1) only explains the marker convention, so it is not a row (D-100 (5) precedent).

  line 2        s0 = sunday_on_or_before(current_date)     start()
  line 3        tenure T1 opens on s0 (owner only)         start()
  line 4        SET ROLE labapp                            start() uses the app connection
  lines 5-6     pool + Components envelopes                start()
  line 7        members A, B, C                            start()
  line 8        membership periods (C ends on s0+3)        start()
  lines 9-10    deposit 500 into Components                start() (ledger_entry)
  lines 11-12   expense -300 'Component purchase'          start() (ledger_entry)
  lines 13-17   four assets                                start()
  line 19       \echo prose
  lines 20-24   acquisitions (ESP32 linked to purchase)    T3 (acquisitions())
                 line 23's Raspberry Pi purchase is
                 INCOMPLETE in the example (no link);
                 the ported seed corrects it under
                 explicit approval (D-165)                   T3 (acquisitions())
  line 26       \echo prose
  lines 27-31   lend 4 to A, return 1, damage 1 with A     T4 (lend_cycle())
  line 32       \echo prose
  lines 33-36   Pi damage/repair, Multimeter damage/lend   T4 (lend_cycle())
  line 37       EXPECT ESP32 7/1/2, Pi stock 1,
                Multimeter 1/1/1, queue shows Multimeter   T5
  line 38       asset_overview SELECT                      T5
  line 39       admin_replacement_queue SELECT             T5
  line 40       \echo prose
  lines 41-44   exchanged, replacement, lost, scrapped     T6 (exchange_cycle())
  lines 45-46   correction -1                              T6 (exchange_cycle())
  line 47       EXPECT ESP32 5/0/2/1/1, Multimeter
                2/0/1 exch 1                               T7
  line 48       asset_overview SELECT                      T7
  line 49       who_has_what SELECT                        T7
  line 51       \echo prose
  line 52       mistaken lend of 2 to B                    T8 (setup)
  lines 53-58   reversal + replacement in ONE transaction  T8
  line 59       asset_events_current shows one line        T8
  line 60       \echo prose
  lines 61-63   note edit with app.actor='treasurer'       T9
  line 64       asset_label_edits SELECT                   T9
  line 66       \echo 'EXPECT FAIL x N' header             T10 (prose; the rows follow)
  line 67       lend 20 (not enough in stock)              T10[beyond-stock]
  line 68       return 5 (member holds fewer)              T10[over-return]
  line 69       lend to a member whose period ended        T10[gone-member]
  line 70       lend without a member                      T10[no-member]
  line 71       acquired without a source                  T10[no-source]
  line 72       repaired with a source                     T10[repaired-source]
  line 73       correction with a member                   T10[correction-member]
  line 74       a second individual Oscilloscope           T10[individual-duplicate]
  line 75       lending 2 of an individual asset           T10[individual-two-units]
  line 76       damaged without the required note          T10[damaged-without-note]
  line 77       acquired with a negative quantity          T10[negative-acquire]
  lines 78-79   a second reversal of the mistaken lend
                (its reverses_id column is still NULL;
                mirror check rejects the -1)               T10[re-reverse]
  lines 80-81   reversing a reversal                       T10[reverse-the-reversal]
  line 82       UPDATE quantity (labapp lacks the column
                grant; 42501 before the trigger)           T10[edit-quantity]
  line 83       DELETE event (labapp lacks DELETE;
                42501 before the trigger)                  T10[delete-event]
  line 84       UPDATE mode                                T10[edit-mode]
  line 85       UPDATE name (ALLOWED: asset_guard only
                blocks mode/ownership; labapp may rename)  T11
  line 86       RESET ROLE                                 no statement; conftest swaps connections
  line 87       \echo prose (corrections collapsed)        T12
  line 88       asset_activity numbers                     T12
  line 89       \echo 'health: EXPECT 0 rows'
  line 90       verify_all()                               T13
  lines 92-95   final lend, close_tenure('T2')             T14 (close_the_tenure())
  lines 96-97   snapshot counts                            T14
  line 98       holding rows                               T14
  line 99       \echo 'EXPECT FAIL: closed tenure'
  line 100      return inside the closed tenure            T15[closed-return]
  line 101      note edit inside the closed tenure         T15[closed-note]
  lines 102-103 reversing a closed-tenure acquisition     T15[closed-reverse]
  lines 104-106 the T2 return is accepted                  T16
  line 108      \echo 'health after close: EXPECT 0 rows'
  line 109      verify_all()                               T17
  lines 110-113 superuser tamper (trigger disabled)        T18 (setup)
  line 114      verify_all() finds the drift               T18

Rejected statements run in the state the script has when it reaches them (`fixed_prefix`),
so each assertion pins the class PostgreSQL really raises: trigger and function refusals are
P0001 (`RaiseError`), table CHECKs are 23514 (`CheckViolationError`); all 16 rejected
statements of the script raise: 14 are trigger or CHECK refusals (P0001 `RaiseError` /
23514 `CheckViolationError`) and lines 82-83 hit the labapp privilege wall (42501
`InsufficientPrivilegeError`, D-100's lesson); the name edit on line 85 is the one statement
that may succeed, and it is pinned as allowed by T11. Note `reverses_id` lives on the
REVERSAL row (db/schema.sql:670): an original keeps its NULL, which is why lines 78-79 find
the mistaken lend again and die on the mirror check instead of being a silent no-op. The
stock arithmetic in
`asset_event_effects` (db/schema.sql:696-714) makes `scrapped`/`exchanged` not touch `stock`,
which is why the script's EXPECT numbers are exact. Dates are relative to the current Sunday
(`s0`; D-045/D-099).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import asyncpg
import pytest

from tests.conftest import TestDb

POOL_UNUSED = 1  # the pool exists but plays no role in this example
COMPONENTS = 2
ONE_DAY = timedelta(days=1)

OSCILLOSCOPE, PI, ESP32, MULTIMETER = 1, 2, 3, 4


@dataclass
class AssetState:
    """One `asset_overview` row (the counts the two EXPECT lines state)."""

    ownership: str
    stock: int
    damaged: int
    held: int
    lost: int
    scrapped: int
    exchanged: int


async def ledger_entry(
    conn: asyncpg.Connection,
    kind: str,
    lines: list[tuple[int, int]],
    *,
    on: date,
    **cols: Any,
) -> int:
    """Write one ledger entry (header + lines) in ONE transaction; returns its id."""
    keys = ["tenure_id", "kind", "occurred_on", "recorded_by", *cols]
    values = [1, kind, on, "treasurer", *cols.values()]
    placeholders = ",".join(f"${i + 1}" for i in range(len(keys)))
    async with conn.transaction():
        tx: int = await conn.fetchval(
            f"INSERT INTO ledger_transactions({','.join(keys)}) VALUES ({placeholders})"
            " RETURNING id",
            *values,
        )
        for envelope_id, amount in lines:
            await conn.execute(
                "INSERT INTO ledger_lines(transaction_id, envelope_id, amount) VALUES ($1,$2,$3)",
                tx,
                envelope_id,
                amount,
            )
    return tx


async def ev(
    conn: asyncpg.Connection,
    asset_id: int,
    kind: str,
    quantity: int,
    *,
    on: date,
    member_id: int | None = None,
    source: str | None = None,
    note: str | None = None,
    ledger_tx: int | None = None,
    reverses_id: int | None = None,
    replaces_id: int | None = None,
) -> int:
    """Insert one asset event with only the columns the script supplies; returns its id."""
    keys = ["asset_id", "kind", "quantity", "occurred_on", "recorded_by"]
    values: list[Any] = [asset_id, kind, quantity, on, "treasurer"]
    for key, value in (
        ("member_id", member_id),
        ("source", source),
        ("note", note),
        ("ledger_transaction_id", ledger_tx),
        ("reverses_id", reverses_id),
        ("replaces_id", replaces_id),
    ):
        if value is not None:
            keys.append(key)
            values.append(value)
    columns = ",".join(keys)
    placeholders = ",".join(f"${i + 1}" for i in range(len(keys)))
    event_id: int = await conn.fetchval(
        f"INSERT INTO asset_events({columns}) VALUES ({placeholders}) RETURNING id", *values
    )
    return event_id


async def overview(conn: asyncpg.Connection) -> dict[str, AssetState]:
    """Every `asset_overview` row, keyed by asset name."""
    rows: list[Any] = await conn.fetch(
        "SELECT asset_name, ownership, stock, damaged, with_members, lost, scrapped, exchanged"
        " FROM asset_overview"
    )
    return {
        str(row["asset_name"]): AssetState(
            ownership=str(row["ownership"]),
            stock=int(row["stock"]),
            damaged=int(row["damaged"]),
            held=int(row["with_members"]),
            lost=int(row["lost"]),
            scrapped=int(row["scrapped"]),
            exchanged=int(row["exchanged"]),
        )
        for row in rows
    }


async def start(db: TestDb) -> date:
    """Lines 2-17: tenure T1, two envelopes, three members, two entries, four assets."""
    s0: date = await db.app.fetchval("SELECT sunday_on_or_before(current_date)")
    await db.owner.execute("INSERT INTO tenures(name, opened_on) VALUES ('T1', $1)", s0)
    await db.app.execute(
        "INSERT INTO envelopes(name, is_pool) VALUES ('Unallocated General', true)"
    )
    await db.app.execute("INSERT INTO envelopes(name) VALUES ('Components and Equipment')")
    await db.app.execute("INSERT INTO members(name) VALUES ('A'),('B'),('C')")
    await db.app.execute(
        "INSERT INTO membership_periods(member_id, start_date, end_date)"
        " VALUES (1,$1,NULL),(2,$1,NULL),(3,$1,$1::date + 3)",
        s0,
    )
    await ledger_entry(db.app, "deposit", [(COMPONENTS, 500)], on=s0, source="other")
    await ledger_entry(
        db.app, "expense", [(COMPONENTS, -300)], on=s0 + ONE_DAY, tag="Component purchase"
    )
    await db.app.execute(
        "INSERT INTO assets(name, mode, ownership, tag) VALUES"
        " ('Oscilloscope','individual','admin','ADM-001'),"
        " ('Raspberry Pi 5','individual','lab','PI5-01'),"
        " ('ESP32 DevKit','counted','lab',NULL),"
        " ('Multimeter','counted','admin',NULL)"
    )
    return s0


async def acquisitions(db: TestDb, s0: date) -> int:
    """Lines 20-24: four acquire events; the ESP32 links to the purchase entry."""
    purchase_tx: int = await db.app.fetchval("SELECT max(id) FROM ledger_transactions")
    esp32 = await ev(
        db.app, ESP32, "acquired", 10, on=s0 + ONE_DAY, source="purchase", ledger_tx=purchase_tx
    )
    await ev(db.app, OSCILLOSCOPE, "acquired", 1, on=s0, source="admin")
    await ev(db.app, PI, "acquired", 1, on=s0 + ONE_DAY, source="purchase", ledger_tx=purchase_tx)
    await ev(db.app, MULTIMETER, "acquired", 3, on=s0, source="admin")
    return esp32


async def lend_cycle(db: TestDb, s0: date) -> None:
    """Lines 27-36: lends, a return, damages and a repair."""
    await ev(
        db.app,
        ESP32,
        "lent",
        4,
        on=s0 + 2 * ONE_DAY,
        member_id=1,
        note="for weather-station project",
    )
    await ev(db.app, ESP32, "returned", 1, on=s0 + 3 * ONE_DAY, member_id=1)
    await ev(
        db.app,
        ESP32,
        "damaged",
        1,
        on=s0 + 3 * ONE_DAY,
        member_id=1,
        note="burnt, reverse polarity",
    )
    await ev(db.app, PI, "damaged", 1, on=s0 + 3 * ONE_DAY, note="overheated")
    await ev(db.app, PI, "repaired", 1, on=s0 + 4 * ONE_DAY)
    await ev(db.app, MULTIMETER, "damaged", 1, on=s0 + 3 * ONE_DAY, note="dead display")
    await ev(db.app, MULTIMETER, "lent", 1, on=s0 + 2 * ONE_DAY, member_id=3)


async def exchange_cycle(db: TestDb, s0: date) -> None:
    """Lines 41-46: exchange with admin, the replacement, lost, scrapped, correction."""
    await ev(
        db.app,
        MULTIMETER,
        "exchanged",
        1,
        on=s0 + 5 * ONE_DAY,
        note="sent to admin for replacement",
    )
    await ev(
        db.app,
        MULTIMETER,
        "acquired",
        1,
        on=s0 + 6 * ONE_DAY,
        source="replacement",
        note="replacement from admin",
    )
    await ev(db.app, ESP32, "lost", 1, on=s0 + 6 * ONE_DAY, note="missing after workshop")
    await ev(db.app, ESP32, "scrapped", 1, on=s0 + 6 * ONE_DAY, note="not repairable")
    await ev(db.app, ESP32, "correction", -1, on=s0 + 7 * ONE_DAY, note="physical count found 5")


async def first_cycle(db: TestDb) -> date:
    """Lines 2-36: setup plus acquisitions and the lend/return/damage/repair flow."""
    s0 = await start(db)
    await acquisitions(db, s0)
    await lend_cycle(db, s0)
    return s0


async def second_cycle(db: TestDb) -> date:
    """Lines 2-46: first cycle plus the exchange/replacement/lost/scrapped/correction block."""
    s0 = await first_cycle(db)
    await exchange_cycle(db, s0)
    return s0


async def fix_mistaken_lend(db: TestDb, s0: date) -> tuple[int, int, int]:
    """Lines 52-58: the mistaken lend, then reversal + replacement in ONE transaction."""
    mistake = await ev(db.app, ESP32, "lent", 2, on=s0 + 8 * ONE_DAY, member_id=2, note="robot arm")
    async with db.app.transaction():
        reversal = await ev(
            db.app,
            ESP32,
            "lent",
            -2,
            on=s0 + 8 * ONE_DAY,
            member_id=2,
            reverses_id=mistake,
            note="typo, should be 1",
        )
        replacement = await ev(
            db.app,
            ESP32,
            "lent",
            1,
            on=s0 + 8 * ONE_DAY,
            member_id=2,
            replaces_id=mistake,
            note="robot arm",
        )
    return mistake, reversal, replacement


async def note_edit(db: TestDb) -> None:
    """Lines 61-63: rename the replacement's note as the treasurer; the edit is logged."""
    async with db.app.transaction():
        await db.app.execute("SET LOCAL app.actor = 'treasurer'")
        await db.app.execute(
            "UPDATE asset_events SET note = 'robot arm project'"
            " WHERE asset_id = 3 AND member_id = 2 AND quantity = 1 AND reverses_id IS NULL"
        )


async def fixed_prefix(db: TestDb) -> date:
    """Lines 2-64: everything through the fixed lend and the logged note edit."""
    s0 = await second_cycle(db)
    await fix_mistaken_lend(db, s0)
    await note_edit(db)
    return s0


async def activity_prefix(db: TestDb) -> date:
    """Lines 2-88: the fixed prefix, the (no-op) rejections and the allowed rename."""
    s0 = await fixed_prefix(db)
    await db.app.execute("UPDATE assets SET name = 'Oscilloscope (Rigol)' WHERE id = 1")
    return s0


async def close_the_tenure(db: TestDb, s0: date) -> int:
    """Lines 93-95: the final Multimeter lend, then close tenure and open T2."""
    await ev(db.app, MULTIMETER, "lent", 1, on=s0 + 9 * ONE_DAY, member_id=1)
    new_id: int = await db.app.fetchval(
        "SELECT close_tenure($1::date + $2::int, 'treasurer', 'T2')", s0, 10
    )
    return new_id


async def handover_prefix(db: TestDb) -> date:
    """Lines 2-95: everything through the closed tenure."""
    s0 = await fixed_prefix(db)
    await close_the_tenure(db, s0)
    return s0


async def test_setup_replays_example_prefix(db: TestDb) -> None:
    """Lines 2-17: the setup succeeds exactly as scripted."""
    s0 = await start(db)
    assert await db.app.fetchval("SELECT count(*) FROM ledger_transactions") == 2
    assert await db.app.fetchval("SELECT count(*) FROM assets") == 4
    periods: list[Any] = await db.app.fetch(
        "SELECT member_id, start_date, end_date FROM membership_periods ORDER BY member_id"
    )
    assert [(int(r["member_id"]), r["start_date"], r["end_date"]) for r in periods] == [
        (1, s0, None),
        (2, s0, None),
        (3, s0, s0 + 3 * ONE_DAY),
    ]


async def test_assets_are_created(db: TestDb) -> None:
    """Lines 13-17: the four assets with their modes, owners and tags."""
    await start(db)
    rows: list[Any] = await db.app.fetch(
        "SELECT name, mode, ownership, tag FROM assets ORDER BY id"
    )
    assert [(r["name"], r["mode"], r["ownership"], r["tag"]) for r in rows] == [
        ("Oscilloscope", "individual", "admin", "ADM-001"),
        ("Raspberry Pi 5", "individual", "lab", "PI5-01"),
        ("ESP32 DevKit", "counted", "lab", None),
        ("Multimeter", "counted", "admin", None),
    ]


async def test_acquisitions_succeed(db: TestDb) -> None:
    """Lines 20-24: four acquire events; the ESP32's links to the purchase entry."""
    s0 = await start(db)
    esp32 = await acquisitions(db, s0)
    rows: list[Any] = await db.app.fetch(
        "SELECT asset_id, kind, quantity, source, ledger_transaction_id FROM asset_events"
        " WHERE kind = 'acquired' ORDER BY id"
    )
    purchase_tx: int = await db.app.fetchval("SELECT max(id) FROM ledger_transactions")
    assert [
        (
            int(r["asset_id"]),
            r["kind"],
            int(r["quantity"]),
            r["source"],
            None if r["ledger_transaction_id"] is None else int(r["ledger_transaction_id"]),
        )
        for r in rows
    ] == [
        (ESP32, "acquired", 10, "purchase", purchase_tx),
        (OSCILLOSCOPE, "acquired", 1, "admin", None),
        (PI, "acquired", 1, "purchase", purchase_tx),
        (MULTIMETER, "acquired", 3, "admin", None),
    ]
    assert esp32 > 0


async def test_a_purchase_must_name_its_payment(db: TestDb) -> None:
    """Issue #11: a `purchase` acquisition without a ledger link is refused by the database.

    The rule is owned by PostgreSQL, not by the app, so every writer is bound by it
    (direct SQL, the future Go backend). The refusal is the table CHECK
    `asset_purchase_needs_link` -> SQLSTATE 23514 (`CheckViolationError`).
    """
    s0 = await start(db)
    with pytest.raises(asyncpg.CheckViolationError) as exc:
        await db.app.execute(
            "INSERT INTO asset_events(asset_id, kind, quantity, occurred_on, recorded_by, source)"
            " VALUES (3, 'acquired', 1, $1::date, 'treasurer', 'purchase')",
            s0,
        )
    assert exc.value.constraint_name == "asset_purchase_needs_link"


async def test_a_purchase_with_a_link_is_accepted(db: TestDb) -> None:
    """Issue #11: the new CHECK refuses only the LINKLESS purchase; a linked one is fine."""
    s0 = await start(db)
    purchase_tx: int = await db.app.fetchval("SELECT max(id) FROM ledger_transactions")
    await db.app.execute(
        "INSERT INTO asset_events"
        "(asset_id, kind, quantity, occurred_on, recorded_by, source, ledger_transaction_id)"
        " VALUES (3, 'acquired', 1, $1::date, 'treasurer', 'purchase', $2)",
        s0,
        purchase_tx,
    )
    linked = await db.app.fetchval(
        "SELECT ledger_transaction_id FROM asset_events WHERE asset_id = 3"
    )
    assert int(linked) == purchase_tx


async def test_a_non_purchase_acquisition_needs_no_link(db: TestDb) -> None:
    """Issue #11: only `source = 'purchase'` demands a link; `admin` needs none."""
    s0 = await start(db)
    await db.app.execute(
        "INSERT INTO asset_events(asset_id, kind, quantity, occurred_on, recorded_by, source)"
        " VALUES (3, 'acquired', 1, $1::date, 'treasurer', 'admin')",
        s0,
    )
    rows: list[Any] = await db.app.fetch(
        "SELECT source::text AS source, ledger_transaction_id FROM asset_events"
        " WHERE asset_id = 3 AND kind = 'acquired'"
    )
    assert len(rows) == 1
    assert rows[0]["source"] == "admin"
    assert rows[0]["ledger_transaction_id"] is None


async def test_lend_return_damage_repair_flow(db: TestDb) -> None:
    """Lines 27-36: every event of the first lend/damage/repair cycle is accepted."""
    s0 = await first_cycle(db)
    rows: list[Any] = await db.app.fetch(
        "SELECT asset_id, kind, quantity, member_id FROM asset_events"
        " WHERE kind <> 'acquired' ORDER BY id"
    )
    assert [
        (
            int(r["asset_id"]),
            r["kind"],
            int(r["quantity"]),
            None if r["member_id"] is None else int(r["member_id"]),
        )
        for r in rows
    ] == [
        (ESP32, "lent", 4, 1),
        (ESP32, "returned", 1, 1),
        (ESP32, "damaged", 1, 1),
        (PI, "damaged", 1, None),
        (PI, "repaired", 1, None),
        (MULTIMETER, "damaged", 1, None),
        (MULTIMETER, "lent", 1, 3),
    ]
    assert s0.weekday() == 6  # the script's whole timeline hangs off a Sunday


async def test_expect_overview_after_first_cycle(db: TestDb) -> None:
    """Line 37: ESP32 7/1/2; Pi stock 1; Multimeter 1/1/1; the queue shows Multimeter."""
    await first_cycle(db)
    state = await overview(db.app)
    assert state["ESP32 DevKit"] == AssetState("lab", 7, 1, 2, 0, 0, 0)
    assert state["Raspberry Pi 5"] == AssetState("lab", 1, 0, 0, 0, 0, 0)
    assert state["Multimeter"] == AssetState("admin", 1, 1, 1, 0, 0, 0)
    assert state["Oscilloscope"].stock == 1
    queue: list[Any] = await db.app.fetch("SELECT asset_name, damaged FROM admin_replacement_queue")
    assert [(r["asset_name"], int(r["damaged"])) for r in queue] == [("Multimeter", 1)]


async def test_exchange_replacement_lost_scrapped_correction(db: TestDb) -> None:
    """Lines 41-46: the exchange cycle and the -1 physical-count correction are accepted."""
    s0 = await second_cycle(db)
    rows: list[Any] = await db.app.fetch(
        "SELECT asset_id, kind, quantity, note FROM asset_events"
        " WHERE occurred_on >= $1 ORDER BY id",
        s0 + 5 * ONE_DAY,
    )
    assert [(int(r["asset_id"]), r["kind"], int(r["quantity"]), r["note"]) for r in rows] == [
        (MULTIMETER, "exchanged", 1, "sent to admin for replacement"),
        (MULTIMETER, "acquired", 1, "replacement from admin"),
        (ESP32, "lost", 1, "missing after workshop"),
        (ESP32, "scrapped", 1, "not repairable"),
        (ESP32, "correction", -1, "physical count found 5"),
    ]


async def test_expect_overview_after_second_cycle(db: TestDb) -> None:
    """Line 47: ESP32 5/0/2/1/1; Multimeter 2/0/1 exch 1; who_has_what as scripted."""
    await second_cycle(db)
    state = await overview(db.app)
    assert state["ESP32 DevKit"] == AssetState("lab", 5, 0, 2, 1, 1, 0)
    assert state["Multimeter"] == AssetState("admin", 2, 0, 1, 0, 0, 1)
    holds: list[Any] = await db.app.fetch(
        "SELECT member_name, asset_name, quantity FROM who_has_what"
    )
    assert [(r["member_name"], r["asset_name"], int(r["quantity"])) for r in holds] == [
        ("A", "ESP32 DevKit", 2),
        ("C", "Multimeter", 1),
    ]


async def test_fix_mistaken_lend_reversal_plus_replacement(db: TestDb) -> None:
    """Lines 51-59: the list shows ONE line; the replacement carries corrected_from."""
    s0 = await second_cycle(db)
    mistake, _reversal, replacement = await fix_mistaken_lend(db, s0)
    rows: list[Any] = await db.app.fetch(
        "SELECT id, kind, quantity, note, corrected_from FROM asset_events_current"
        " WHERE member_id = 2"
    )
    assert [
        (
            int(r["id"]),
            r["kind"],
            int(r["quantity"]),
            r["note"],
            None if r["corrected_from"] is None else int(r["corrected_from"]),
        )
        for r in rows
    ] == [(replacement, "lent", 1, "robot arm", mistake)]
    assert replacement != mistake


async def test_note_edit_is_logged(db: TestDb) -> None:
    """Lines 60-64: the note edit in place lands in asset_label_edits naming the actor."""
    await fixed_prefix(db)
    rows: list[Any] = await db.app.fetch(
        "SELECT field, old_value, new_value, edited_by FROM asset_label_edits"
    )
    assert [(r["field"], r["old_value"], r["new_value"], r["edited_by"]) for r in rows] == [
        ("note", "robot arm", "robot arm project", "treasurer")
    ]


REJECTED_CASES: list[tuple[str, str, int, type[Exception], str]] = [
    (
        "beyond-stock",
        "INSERT INTO asset_events(asset_id, kind, quantity, member_id, occurred_on, recorded_by)"
        " VALUES (3, 'lent', 20, 2, $1::date + $2::int, 'treasurer')",
        9,
        asyncpg.RaiseError,
        "not enough in stock",
    ),
    (
        "over-return",
        "INSERT INTO asset_events(asset_id, kind, quantity, member_id, occurred_on, recorded_by)"
        " VALUES (3, 'returned', 5, 2, $1::date + $2::int, 'treasurer')",
        9,
        asyncpg.RaiseError,
        "that member holds fewer units",
    ),
    (
        "gone-member",
        "INSERT INTO asset_events(asset_id, kind, quantity, member_id, occurred_on, recorded_by)"
        " VALUES (3, 'lent', 1, 3, $1::date + $2::int, 'treasurer')",
        5,
        asyncpg.RaiseError,
        "only a current member can borrow",
    ),
    (
        "no-member",
        "INSERT INTO asset_events(asset_id, kind, quantity, occurred_on, recorded_by)"
        " VALUES (3, 'lent', 1, $1::date + $2::int, 'treasurer')",
        9,
        asyncpg.RaiseError,
        "lending and returning need a member",
    ),
    (
        "no-source",
        "INSERT INTO asset_events(asset_id, kind, quantity, occurred_on, recorded_by)"
        " VALUES (3, 'acquired', 1, $1::date + $2::int, 'treasurer')",
        9,
        asyncpg.CheckViolationError,
        "violates check constraint",
    ),
    (
        "repaired-source",
        "INSERT INTO asset_events(asset_id, kind, quantity, occurred_on, recorded_by, source)"
        " VALUES (3, 'repaired', 1, $1::date + $2::int, 'treasurer', 'purchase')",
        9,
        asyncpg.CheckViolationError,
        "violates check constraint",
    ),
    (
        "correction-member",
        "INSERT INTO asset_events(asset_id, kind, quantity, member_id, occurred_on, recorded_by)"
        " VALUES (3, 'correction', 1, 1, $1::date + $2::int, 'treasurer')",
        9,
        asyncpg.CheckViolationError,
        "violates check constraint",
    ),
    (
        "individual-duplicate",
        "INSERT INTO asset_events(asset_id, kind, quantity, occurred_on, recorded_by, source)"
        " VALUES (1, 'acquired', 1, $1::date + $2::int, 'treasurer', 'admin')",
        9,
        asyncpg.RaiseError,
        "an individually tracked asset can only exist once",
    ),
    (
        "individual-two-units",
        "INSERT INTO asset_events(asset_id, kind, quantity, member_id, occurred_on, recorded_by)"
        " VALUES (2, 'lent', 2, 1, $1::date + $2::int, 'treasurer')",
        9,
        asyncpg.RaiseError,
        "an individually tracked asset moves one unit at a time",
    ),
    (
        "damaged-without-note",
        "INSERT INTO asset_events(asset_id, kind, quantity, occurred_on, recorded_by)"
        " VALUES (3, 'damaged', 1, $1::date + $2::int, 'treasurer')",
        9,
        asyncpg.CheckViolationError,
        "violates check constraint",
    ),
    (
        "negative-acquire",
        "INSERT INTO asset_events(asset_id, kind, quantity, occurred_on, recorded_by, source)"
        " VALUES (3, 'acquired', -3, $1::date + $2::int, 'treasurer', 'purchase')",
        9,
        asyncpg.CheckViolationError,
        "violates check constraint",
    ),
    (
        "re-reverse",
        "INSERT INTO asset_events(asset_id, kind, quantity, member_id, occurred_on, recorded_by,"
        " reverses_id, note)"
        " SELECT 3, 'lent', -1, 2, $1::date + $2::int, 'treasurer', id, 'again'"
        " FROM asset_events WHERE asset_id = 3 AND kind = 'lent' AND member_id = 2"
        " AND quantity = 2 AND reverses_id IS NULL",
        9,
        asyncpg.RaiseError,
        "a reversal must mirror the original event",
    ),
    (
        "reverse-the-reversal",
        "INSERT INTO asset_events(asset_id, kind, quantity, member_id, occurred_on, recorded_by,"
        " reverses_id, note)"
        " SELECT 3, 'lent', 2, 2, $1::date + $2::int, 'treasurer', id, 'undo undo'"
        " FROM asset_events WHERE reverses_id IS NOT NULL AND asset_id = 3 LIMIT 1",
        9,
        asyncpg.RaiseError,
        "cannot be reversed",
    ),
    (
        # labapp may UPDATE only (note, cost_center_id, occurred_on) - db/schema.sql:1200;
        # the privilege wall (42501) fires before asset_event_edit (D-100's lesson)
        "edit-quantity",
        "UPDATE asset_events SET quantity = 99 WHERE id = 1",
        9,
        asyncpg.InsufficientPrivilegeError,
        "permission denied",
    ),
    (
        # labapp has no DELETE grant on asset_events (db/schema.sql:1193-1194);
        # the privilege wall (42501) fires before no_delete_asset_ev
        "delete-event",
        "DELETE FROM asset_events WHERE id = 1",
        9,
        asyncpg.InsufficientPrivilegeError,
        "permission denied",
    ),
    (
        "edit-mode",
        "UPDATE assets SET mode = 'counted' WHERE id = 1",
        9,
        asyncpg.RaiseError,
        "mode and ownership cannot change",
    ),
]


@pytest.mark.parametrize(
    ("sql", "day", "error", "match"),
    [case[1:] for case in REJECTED_CASES],
    ids=[case[0] for case in REJECTED_CASES],
)
async def test_rejected_mistakes(
    db: TestDb, sql: str, day: int, error: type[Exception], match: str
) -> None:
    """Lines 66-84: every rejected mistake raises exactly the class PostgreSQL gives it."""
    s0 = await fixed_prefix(db)
    args: tuple[Any, ...] = (s0, day) if "$1" in sql else ()
    with pytest.raises(error, match=match):
        await db.app.execute(sql, *args)


async def test_asset_name_edit_is_allowed(db: TestDb) -> None:
    """Line 85: renaming an asset is allowed (only mode/ownership changes are guarded)."""
    await start(db)
    await db.app.execute("UPDATE assets SET name = 'Oscilloscope (Rigol)' WHERE id = 1")
    name: str | None = await db.app.fetchval("SELECT name FROM assets WHERE id = 1")
    assert name == "Oscilloscope (Rigol)"


async def test_asset_activity_numbers(db: TestDb) -> None:
    """Line 88: the report's raw numbers; corrections collapsed (the mistaken 2 is gone)."""
    s0 = await activity_prefix(db)
    rows: list[Any] = await db.app.fetch(
        "SELECT asset_name, ownership, kind, source, units, events FROM"
        " asset_activity($1::date, $1::date + $2::int) ORDER BY 1, 3, 4",
        s0,
        9,
    )
    assert [
        (
            r["asset_name"],
            r["ownership"],
            r["kind"],
            None if r["source"] is None else str(r["source"]),
            int(r["units"]),
            int(r["events"]),
        )
        for r in rows
    ] == [
        ("ESP32 DevKit", "lab", "acquired", "purchase", 10, 1),
        ("ESP32 DevKit", "lab", "lent", None, 5, 2),
        ("ESP32 DevKit", "lab", "returned", None, 1, 1),
        ("ESP32 DevKit", "lab", "damaged", None, 1, 1),
        ("ESP32 DevKit", "lab", "lost", None, 1, 1),
        ("ESP32 DevKit", "lab", "scrapped", None, 1, 1),
        ("ESP32 DevKit", "lab", "correction", None, -1, 1),
        ("Multimeter", "admin", "acquired", "admin", 3, 1),
        ("Multimeter", "admin", "acquired", "replacement", 1, 1),
        ("Multimeter", "admin", "lent", None, 1, 1),
        ("Multimeter", "admin", "damaged", None, 1, 1),
        ("Multimeter", "admin", "exchanged", None, 1, 1),
        ("Oscilloscope (Rigol)", "admin", "acquired", "admin", 1, 1),
        ("Raspberry Pi 5", "lab", "acquired", "purchase", 1, 1),
        ("Raspberry Pi 5", "lab", "damaged", None, 1, 1),
        ("Raspberry Pi 5", "lab", "repaired", None, 1, 1),
    ]


async def test_the_database_stays_healthy(db: TestDb) -> None:
    """Lines 89-90: the whole asset lifecycle leaves a healthy database."""
    await fixed_prefix(db)
    problems: list[Any] = await db.app.fetch("SELECT * FROM verify_all()")
    assert problems == []


async def test_close_tenure_writes_the_handover_register(db: TestDb) -> None:
    """Lines 92-98: close_tenure snapshots every asset and every holding."""
    s0 = await fixed_prefix(db)
    new_id = await close_the_tenure(db, s0)
    assert new_id == 2
    assert await db.app.fetchval("SELECT count(*) AS asset_rows FROM tenure_asset_snapshots") == 4
    assert (
        await db.app.fetchval("SELECT count(*) AS holding_rows FROM tenure_holding_snapshots") == 4
    )
    rows: list[Any] = await db.app.fetch(
        "SELECT m.name AS member, a.name AS asset, h.quantity FROM tenure_holding_snapshots h"
        " JOIN members m ON m.id = h.member_id JOIN assets a ON a.id = h.asset_id ORDER BY 1, 2"
    )
    assert [(r["member"], r["asset"], int(r["quantity"])) for r in rows] == [
        ("A", "ESP32 DevKit", 2),
        ("A", "Multimeter", 1),
        ("B", "ESP32 DevKit", 1),
        ("C", "Multimeter", 1),
    ]


CLOSED_CASES: list[tuple[str, int, str, type[Exception], str]] = [
    (
        "closed-return",
        9,
        "INSERT INTO asset_events(asset_id, kind, quantity, member_id, occurred_on, recorded_by)"
        " VALUES (3, 'returned', 1, 1, $1::date + $2::int, 'treasurer')",
        asyncpg.RaiseError,
        "inside a closed tenure",
    ),
    (
        "closed-note",
        0,
        "UPDATE asset_events SET note = 'sneaky' WHERE asset_id = 3 AND kind = 'acquired'",
        asyncpg.RaiseError,
        "belongs to a closed tenure",
    ),
    (
        "closed-reverse",
        11,
        "INSERT INTO asset_events(asset_id, kind, quantity, occurred_on, recorded_by, source,"
        " reverses_id, note)"
        " SELECT 3, 'acquired', -10, $1::date + $2::int, 'treasurer', 'purchase', id, 'oops'"
        " FROM asset_events WHERE asset_id = 3 AND kind = 'acquired'",
        asyncpg.RaiseError,
        "cannot be reversed",
    ),
]


@pytest.mark.parametrize(
    ("day", "sql", "error", "match"),
    [case[1:] for case in CLOSED_CASES],
    ids=[case[0] for case in CLOSED_CASES],
)
async def test_closed_tenure_touches_are_rejected(
    db: TestDb, day: int, sql: str, error: type[Exception], match: str
) -> None:
    """Lines 99-103: nothing may be written into, or out of, the closed tenure."""
    s0 = await handover_prefix(db)
    args: tuple[Any, ...] = (s0, day) if "$1" in sql else ()
    with pytest.raises(error, match=match):
        await db.app.execute(sql, *args)


async def test_the_new_tenure_carries_on(db: TestDb) -> None:
    """Lines 104-106: A returns the Multimeter in T2; the counts follow."""
    s0 = await handover_prefix(db)
    await ev(db.app, MULTIMETER, "returned", 1, on=s0 + 11 * ONE_DAY, member_id=1)
    state = await overview(db.app)
    assert (state["Multimeter"].stock, state["Multimeter"].held) == (2, 1)


async def test_the_database_is_healthy_after_close(db: TestDb) -> None:
    """Lines 108-109: the handover itself leaves a healthy database."""
    await handover_prefix(db)
    problems: list[Any] = await db.app.fetch("SELECT * FROM verify_all()")
    assert problems == []


async def test_superuser_tamper_is_detected(db: TestDb) -> None:
    """Lines 110-114: a smuggled quantity edit shows up as one verify_all() problem."""
    s0 = await handover_prefix(db)
    await ev(db.app, MULTIMETER, "returned", 1, on=s0 + 11 * ONE_DAY, member_id=1)
    await db.owner.execute("ALTER TABLE asset_events DISABLE TRIGGER asset_event_edit")
    await db.owner.execute(
        "UPDATE asset_events SET quantity = 11 WHERE asset_id = 3 AND kind = 'acquired'"
    )
    await db.owner.execute("ALTER TABLE asset_events ENABLE TRIGGER asset_event_edit")
    problems: list[Any] = await db.app.fetch("SELECT * FROM verify_all()")
    assert len(problems) == 1
    assert 'tenure "T1": asset "ESP32 DevKit" changed after close' in problems[0]["problem"]
