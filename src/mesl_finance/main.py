"""Composition root: the only module that knows every layer and wires adapters to ports."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import FastAPI

from mesl_finance.auth.api.router import router as auth_router
from mesl_finance.auth.application.login import Login
from mesl_finance.auth.infrastructure.credentials import Argon2CredentialChecker
from mesl_finance.auth.infrastructure.tokens import JwtTokenService
from mesl_finance.cost_centers.api.router import router as cost_centers_router
from mesl_finance.cost_centers.application.create_cost_center import CreateCostCenter
from mesl_finance.cost_centers.application.list_cost_centers import ListCostCenters
from mesl_finance.cost_centers.application.rename_cost_center import RenameCostCenter
from mesl_finance.cost_centers.application.set_cost_center_status import SetCostCenterStatus
from mesl_finance.cost_centers.infrastructure.unit_of_work import SqlCostCenterUnitOfWork
from mesl_finance.envelopes.api.router import router as envelopes_router
from mesl_finance.envelopes.application.create_envelope import CreateEnvelope
from mesl_finance.envelopes.application.deactivate_envelope import DeactivateEnvelope
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
from mesl_finance.shared.api.problems import install_error_handlers
from mesl_finance.shared.infrastructure.database import create_engine
from mesl_finance.shared.settings import Settings

API_PREFIX = "/api/v1"


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

    app = FastAPI(title="MESL Finance", lifespan=lifespan)
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

    def cost_center_unit_of_work(actor: str) -> SqlCostCenterUnitOfWork:
        return SqlCostCenterUnitOfWork(engine, actor)

    app.state.create_cost_center = CreateCostCenter(cost_center_unit_of_work)
    app.state.list_cost_centers = ListCostCenters(cost_center_unit_of_work)
    app.state.rename_cost_center = RenameCostCenter(cost_center_unit_of_work)
    app.state.set_cost_center_status = SetCostCenterStatus(cost_center_unit_of_work)

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

    install_error_handlers(app)
    app.include_router(auth_router, prefix=API_PREFIX)
    app.include_router(ledger_router, prefix=API_PREFIX)
    app.include_router(envelopes_router, prefix=API_PREFIX)
    app.include_router(cost_centers_router, prefix=API_PREFIX)
    app.include_router(members_router, prefix=API_PREFIX)
    app.include_router(fees_router, prefix=API_PREFIX)
    return app
