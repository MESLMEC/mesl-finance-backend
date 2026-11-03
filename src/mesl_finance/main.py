"""Composition root: the only module that knows every layer and wires adapters to ports."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import FastAPI

from mesl_finance.assets.api.router import router as assets_router
from mesl_finance.assets.application.create_asset import CreateAsset
from mesl_finance.assets.application.edit_asset import EditAsset
from mesl_finance.assets.application.fix_event import FixAssetEvent
from mesl_finance.assets.application.list_asset_activity import ListAssetActivity
from mesl_finance.assets.application.list_assets import ListAssets
from mesl_finance.assets.application.read_asset_state import (
    ListAssetState,
    ListReplacementQueue,
    ListWhoHasWhat,
)
from mesl_finance.assets.application.record_event import RecordAssetEvent
from mesl_finance.assets.infrastructure.unit_of_work import SqlAssetUnitOfWork
from mesl_finance.auth.api.router import router as auth_router
from mesl_finance.auth.application.login import Login
from mesl_finance.auth.infrastructure.credentials import Argon2CredentialChecker
from mesl_finance.auth.infrastructure.tokens import JwtTokenService
from mesl_finance.cost_centers.api.router import router as cost_centers_router
from mesl_finance.cost_centers.application.create_cost_center import CreateCostCenter
from mesl_finance.cost_centers.application.get_cost_center_summary import (
    GetCostCenterSummary,
)
from mesl_finance.cost_centers.application.list_cost_centers import ListCostCenters
from mesl_finance.cost_centers.application.rename_cost_center import RenameCostCenter
from mesl_finance.cost_centers.application.set_cost_center_status import SetCostCenterStatus
from mesl_finance.cost_centers.application.sweep_leftover import SweepLeftover
from mesl_finance.cost_centers.infrastructure.unit_of_work import SqlCostCenterUnitOfWork
from mesl_finance.envelopes.api.router import router as envelopes_router
from mesl_finance.envelopes.application.confirm_allocation import ConfirmAllocation
from mesl_finance.envelopes.application.create_envelope import CreateEnvelope
from mesl_finance.envelopes.application.deactivate_envelope import DeactivateEnvelope
from mesl_finance.envelopes.application.draft_allocation import DraftAllocation
from mesl_finance.envelopes.application.get_allocation_context import GetAllocationContext
from mesl_finance.envelopes.application.list_envelopes import ListEnvelopes
from mesl_finance.envelopes.application.rename_envelope import RenameEnvelope
from mesl_finance.envelopes.application.update_envelope_settings import UpdateEnvelopeSettings
from mesl_finance.envelopes.infrastructure.unit_of_work import SqlEnvelopeUnitOfWork
from mesl_finance.fees.api.router import router as fees_router
from mesl_finance.fees.application.create_fee_rate import CreateFeeRate
from mesl_finance.fees.application.list_dues import ListDues
from mesl_finance.fees.application.list_fee_rates import ListFeeRates
from mesl_finance.fees.application.list_shutdown_events import ListShutdownEvents
from mesl_finance.fees.application.set_shutdown import SetShutdown
from mesl_finance.fees.infrastructure.unit_of_work import SqlFeeUnitOfWork
from mesl_finance.health.api.router import router as health_router
from mesl_finance.health.application.check_health import CheckHealth
from mesl_finance.health.infrastructure.unit_of_work import SqlHealthUnitOfWork
from mesl_finance.ledger.api.router import router as ledger_router
from mesl_finance.ledger.application.edit_labels import EditLabels
from mesl_finance.ledger.application.fix_amount import FixAmount
from mesl_finance.ledger.application.list_entries import ListEntries
from mesl_finance.ledger.application.record_deposit import RecordDeposit
from mesl_finance.ledger.application.record_expense import RecordExpense
from mesl_finance.ledger.application.record_refund import RecordRefund
from mesl_finance.ledger.application.record_transfer import RecordTransfer
from mesl_finance.ledger.infrastructure.unit_of_work import SqlLedgerUnitOfWork
from mesl_finance.members.api.router import router as members_router
from mesl_finance.members.application.create_member import CreateMember
from mesl_finance.members.application.edit_member import EditMember
from mesl_finance.members.application.end_membership import EndMembership
from mesl_finance.members.application.list_adjustments import ListAdjustments
from mesl_finance.members.application.list_members import ListMembers
from mesl_finance.members.application.list_membership_periods import ListMembershipPeriods
from mesl_finance.members.application.record_adjustment import RecordAdjustment
from mesl_finance.members.application.start_membership import StartMembership
from mesl_finance.members.infrastructure.unit_of_work import SqlMemberUnitOfWork
from mesl_finance.reconciliation.api.router import router as reconciliation_router
from mesl_finance.reconciliation.application.read_reconciliation import (
    GetReconciliationStatus,
    ListDifferenceSuspects,
    ListUnverifiedEntries,
)
from mesl_finance.reconciliation.application.reconcile import Reconcile
from mesl_finance.reconciliation.infrastructure.unit_of_work import SqlReconciliationUnitOfWork
from mesl_finance.shared.api.problems import install_error_handlers
from mesl_finance.shared.infrastructure.database import create_engine
from mesl_finance.shared.settings import Settings
from mesl_finance.tenures.api.router import router as tenures_router
from mesl_finance.tenures.application.close_tenure import CloseTenure
from mesl_finance.tenures.application.read_snapshots import (
    ListAssetSnapshots,
    ListHoldingSnapshots,
    ListMemberSnapshots,
)
from mesl_finance.tenures.infrastructure.unit_of_work import SqlTenureUnitOfWork

API_PREFIX = "/api/v1"

# The guide (issue #12). Everything below surfaces through the generated
# `docs/openapi.json` into `/docs` (Swagger, try things) and `/redoc` (ReDoc,
# read it). The words are cites: rules live in db/schema.sql and DECISIONS.md.
OVERVIEW = """MESL Finance: the money, members, fees and assets of the lab.
PostgreSQL owns every rule (db/schema.sql); these endpoints call them in one
transaction each and translate what they refuse — nothing here invents a rule.

The money in one breath:
- Every income lands first in the envelope named "Unallocated General" (the pool):
  `POST /envelopes` never creates it (the bootstrap does) and `POST /deposits`
  without `envelope_id` is where it goes.
- The committee then splits the pool with `POST /allocation-suggestion` (dry run)
  and `POST /allocations` (the real split).
- Members owe weekly fees (B-05): `POST /deposits` with `source="weekly_fee"`
  and the member id; refunds go back out through `POST /refunds` — both move
  only the pool.
- An event or project tracks its own money through a cost center:
  in via deposits/expenses with `cost_center_id`, watched at
  `GET /cost-centers/{id}/summary`, leftovers swept back with `POST /sweeps`
  (B-16).
- Month end: `GET /dues` is who owes what; `POST /reconciliations` records the
  pocket-notes count, `GET /reconciliation-status` / `/unverified-entries` /
  `/difference-suspects` say what still needs a look (B-20). `GET /health`
  runs the database's own integrity checks.
- When a committee hands over, `POST /tenures/close` locks the closed tenure,
  writes the snapshots and opens the next one (B-18/B-25).

Rules you would otherwise think are bugs:
- **Money amounts are immutable** — no entry is ever updated or deleted
  (db/schema.sql: append-only + checksums). A wrong amount is CORRECTED, not
  edited: the fix/`fix-amount` endpoints write a reversal plus a replacement in
  one transaction; labels (note, tag, source, date...) stay editable through
  the `edit-labels` action, and every old value is kept in the history tables.
- Every error everywhere is RFC 9457 problem+json: `{code, detail, status,
  title, type}` — the `code` is machine-readable ("rule_violation" means
  PostgreSQL refused; "unknown_reference" names a dead pointer).
- Envelope/cost-center/member lists are id-ordered and never carry computed
  balances; balances are ledger reads.

Read `/redoc` for the per-feature walkthroughs summarized under each tag.
"""

OPENAPI_TAGS = [
    {
        "name": "auth",
        "description": "Log in. The treasurer's username/password come from server settings"
        " (D-006); the bearer JWT they return is accepted by every other route",
    },
    {
        "name": "ledger",
        "description": "The money ledger: deposits in, expenses out, transfers between"
        " envelopes, and the corrections (fix-amount, edit-labels). MONEY IS IMMUTABLE"
        " (D-080/B-18): fix-amount writes a reversal + a replacement in ONE transaction —"
        " there is no edit or delete endpoint, by design. `GET /entries` lists the current"
        " truth (fixed entries collapse into one line); it carries NO amounts on purpose"
        " (db/schema.sql:426-430)",
    },
    {
        "name": "envelopes",
        "description": 'Where money may sit. The pool is named "Unallocated General" and is'
        " created by the first-start bootstrap, never here (D-041); every other envelope maps"
        " a purpose: member projects, lab projects, events, competitions, research, admin"
        " (B-15). Cap + priority are allocation inputs (D-021): the suggestion and "
        "`POST /allocations` fill capped envelopes first by priority, the rest by the"
        " previous session's shares. `deactivate` only works at zero balance",
    },
    {
        "name": "cost-centers",
        "description": "One cost center per event, member project, lab project or competition;"
        " tag money with it as it moves (ledger's `cost_center_id`). The summary shows in/out/"
        "swept/leftover; at an event's end the leftover is swept back to the pool (B-16/B-17)"
        " — no overspend warnings exist on purpose. Kind is fixed at create",
    },
    {
        "name": "members",
        "description": "Who belongs to the lab, membership periods (start once, end once), and"
        " the ledger-side adjustments: waivers (owed week excused), credit donations, opening"
        " balances, corrections. Periods overlap nothing: two open periods are refused"
        " (db/schema.sql:101-102). No auto-expulsion exists (B-09) — dues show raw numbers",
    },
    {
        "name": "fees",
        "description": "The weekly rate (per member, whole BDT; a rate change only affects"
        " future weeks, B-05), shutdown weeks (a national-vacation range that forgives whole"
        " weeks, B-08 — undo a mistake by re-entering the same range with `is_shutdown=false`,"
        " newest row wins), and `GET /dues`: every member, what they owe, credits, and when"
        " arrears started. A member's fee payment is a deposit with source `weekly_fee`"
        " (ledger tag)",
    },
    {
        "name": "assets",
        "description": "What the lab owns and holds. Choose: mode `individual` = one unit per"
        " row (a device, a multimeter serial by tag), mode `counted` = a quantity per row"
        " (kits, components); `ownership` admin = came from the college admin (their damaged"
        " items queue for replacement, `/replacement-queue`), lab = lab money bought it"
        " (db/schema.sql:639-640). Consumables are never tracked (B-21). RECORDING A"
        " PURCHASE: record the expense first (`POST /expenses`), then the acquisition"
        " (kind `acquired`, source `purchase`) must name that payment in"
        " `ledger_transaction_id` — that link is the item's only cost record (D-163,"
        " db/schema.sql 0002). A lent/lost/damaged event names who had it (member_id),"
        " damage needs a note (db/schema.sql rules), lend-to-nothing is refused. Fix an"
        " event via `/events/{event_id}/fix` (reversal + replacement), never an edit",
    },
    {
        "name": "health",
        "description": "The database's self-check (`verify_all`): an empty `[]` means healthy,"
        " problem strings otherwise. Bearer token required: it exposes money detail",
    },
    {
        "name": "reconciliation",
        "description": "Month-end check that pocket notes and the machine agree (B-20)."
        " Count what you hold per envelope, `POST /reconciliations` — matched/answer says"
        " pass or difference. After a match, `/unverified-entries` shrinks to what came"
        " since; `/difference-suspects` guesses which entry explains a difference (the"
        " basics: an extra zero, swapped digits, a same-amount transfer). Entries before"
        " the last match never need review, and nothing to reconcile yet is refused (B-20)",
    },
    {
        "name": "tenures",
        "description": "Committee handover (B-25): `POST /tenures/close` closes the open"
        " tenure on close_on (never before the last entry), writes member/asset/holding"
        " snapshots, opens the NEXT tenure named `next_name` on close_on+1, and carries"
        " balances over as an `opening` entry. The closed tenure is locked forever"
        " (B-18); the snapshots are the handover register",
    },
]


def create_app(settings: Settings | None = None) -> FastAPI:
    """App factory. Run:  uvicorn --app-dir src mesl_finance.main:create_app --factory"""
    config = settings or Settings()  # pyright: ignore[reportCallIssue]
    engine = create_engine(config)
    tokens = JwtTokenService(
        config.jwt_secret.get_secret_value(), ttl=timedelta(hours=config.jwt_ttl_hours)
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
        yield
        await engine.dispose()

    app = FastAPI(
        title="MESL Finance",
        lifespan=lifespan,
        description=OVERVIEW,
        openapi_tags=OPENAPI_TAGS,
    )
    app.state.engine = engine
    app.state.token_service = tokens
    app.state.login = Login(
        Argon2CredentialChecker(config.auth_username, config.auth_password_hash.get_secret_value()),
        tokens,
    )
    app.state.record_deposit = RecordDeposit(lambda actor: SqlLedgerUnitOfWork(engine, actor))
    app.state.record_expense = RecordExpense(lambda actor: SqlLedgerUnitOfWork(engine, actor))
    app.state.record_refund = RecordRefund(lambda actor: SqlLedgerUnitOfWork(engine, actor))
    app.state.record_transfer = RecordTransfer(lambda actor: SqlLedgerUnitOfWork(engine, actor))
    app.state.fix_amount = FixAmount(lambda actor: SqlLedgerUnitOfWork(engine, actor))
    app.state.edit_labels = EditLabels(lambda actor: SqlLedgerUnitOfWork(engine, actor))
    app.state.list_entries = ListEntries(lambda actor: SqlLedgerUnitOfWork(engine, actor))

    def envelope_unit_of_work(actor: str) -> SqlEnvelopeUnitOfWork:
        return SqlEnvelopeUnitOfWork(engine, actor)

    app.state.create_envelope = CreateEnvelope(envelope_unit_of_work)
    app.state.list_envelopes = ListEnvelopes(envelope_unit_of_work)
    app.state.rename_envelope = RenameEnvelope(envelope_unit_of_work)
    app.state.update_envelope_settings = UpdateEnvelopeSettings(envelope_unit_of_work)
    app.state.deactivate_envelope = DeactivateEnvelope(envelope_unit_of_work)
    app.state.get_allocation_context = GetAllocationContext(envelope_unit_of_work)
    app.state.draft_allocation = DraftAllocation(envelope_unit_of_work)
    app.state.confirm_allocation = ConfirmAllocation(envelope_unit_of_work)

    def cost_center_unit_of_work(actor: str) -> SqlCostCenterUnitOfWork:
        return SqlCostCenterUnitOfWork(engine, actor)

    app.state.create_cost_center = CreateCostCenter(cost_center_unit_of_work)
    app.state.list_cost_centers = ListCostCenters(cost_center_unit_of_work)
    app.state.rename_cost_center = RenameCostCenter(cost_center_unit_of_work)
    app.state.set_cost_center_status = SetCostCenterStatus(cost_center_unit_of_work)
    app.state.sweep_leftover = SweepLeftover(cost_center_unit_of_work)
    app.state.get_cost_center_summary = GetCostCenterSummary(cost_center_unit_of_work)

    def member_unit_of_work(actor: str) -> SqlMemberUnitOfWork:
        return SqlMemberUnitOfWork(engine, actor)

    app.state.create_member = CreateMember(member_unit_of_work)
    app.state.list_members = ListMembers(member_unit_of_work)
    app.state.edit_member = EditMember(member_unit_of_work)
    app.state.start_membership = StartMembership(member_unit_of_work)
    app.state.end_membership = EndMembership(member_unit_of_work)
    app.state.list_membership_periods = ListMembershipPeriods(member_unit_of_work)
    app.state.record_adjustment = RecordAdjustment(member_unit_of_work)
    app.state.list_adjustments = ListAdjustments(member_unit_of_work)

    def fee_unit_of_work(actor: str) -> SqlFeeUnitOfWork:
        return SqlFeeUnitOfWork(engine, actor)

    app.state.create_fee_rate = CreateFeeRate(fee_unit_of_work)
    app.state.list_fee_rates = ListFeeRates(fee_unit_of_work)
    app.state.list_dues = ListDues(fee_unit_of_work)
    app.state.set_shutdown = SetShutdown(fee_unit_of_work)
    app.state.list_shutdown_events = ListShutdownEvents(fee_unit_of_work)

    def health_unit_of_work(actor: str) -> SqlHealthUnitOfWork:
        return SqlHealthUnitOfWork(engine, actor)

    app.state.check_health = CheckHealth(health_unit_of_work)

    def asset_unit_of_work(actor: str) -> SqlAssetUnitOfWork:
        return SqlAssetUnitOfWork(engine, actor)

    app.state.create_asset = CreateAsset(asset_unit_of_work)
    app.state.list_assets = ListAssets(asset_unit_of_work)
    app.state.edit_asset = EditAsset(asset_unit_of_work)
    app.state.record_asset_event = RecordAssetEvent(asset_unit_of_work)
    app.state.fix_asset_event = FixAssetEvent(asset_unit_of_work)
    app.state.list_asset_activity = ListAssetActivity(asset_unit_of_work)
    app.state.list_asset_state = ListAssetState(asset_unit_of_work)
    app.state.list_who_has_what = ListWhoHasWhat(asset_unit_of_work)
    app.state.list_replacement_queue = ListReplacementQueue(asset_unit_of_work)

    def reconciliation_unit_of_work(actor: str) -> SqlReconciliationUnitOfWork:
        return SqlReconciliationUnitOfWork(engine, actor)

    app.state.reconcile = Reconcile(reconciliation_unit_of_work)
    app.state.get_reconciliation_status = GetReconciliationStatus(reconciliation_unit_of_work)
    app.state.list_unverified_entries = ListUnverifiedEntries(reconciliation_unit_of_work)
    app.state.list_difference_suspects = ListDifferenceSuspects(reconciliation_unit_of_work)

    def tenure_unit_of_work(actor: str) -> SqlTenureUnitOfWork:
        return SqlTenureUnitOfWork(engine, actor)

    app.state.close_tenure = CloseTenure(tenure_unit_of_work)
    app.state.list_member_snapshots = ListMemberSnapshots(tenure_unit_of_work)
    app.state.list_asset_snapshots = ListAssetSnapshots(tenure_unit_of_work)
    app.state.list_holding_snapshots = ListHoldingSnapshots(tenure_unit_of_work)

    install_error_handlers(app)
    app.include_router(auth_router, prefix=API_PREFIX)
    app.include_router(assets_router, prefix=API_PREFIX)
    app.include_router(ledger_router, prefix=API_PREFIX)
    app.include_router(envelopes_router, prefix=API_PREFIX)
    app.include_router(cost_centers_router, prefix=API_PREFIX)
    app.include_router(members_router, prefix=API_PREFIX)
    app.include_router(fees_router, prefix=API_PREFIX)
    app.include_router(health_router, prefix=API_PREFIX)
    app.include_router(reconciliation_router, prefix=API_PREFIX)
    app.include_router(tenures_router, prefix=API_PREFIX)
    return app
