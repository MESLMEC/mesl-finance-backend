"""Route for the reconciliation action (ROADMAP 10.1)."""

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request

from mesl_finance.auth.api.dependencies import current_actor
from mesl_finance.reconciliation.api.schemas import (
    DifferenceSuspectOut,
    ReconcileOut,
    ReconcileRequest,
    ReconciliationStatusOut,
    UnverifiedEntryOut,
)
from mesl_finance.reconciliation.application.read_reconciliation import (
    GetReconciliationStatus,
    ListDifferenceSuspects,
    ListUnverifiedEntries,
)
from mesl_finance.reconciliation.application.reconcile import Reconcile, ReconcileCommand
from mesl_finance.reconciliation.domain.reconciliation import ReconciliationView
from mesl_finance.reconciliation.domain.reconciliation_reads import (
    DifferenceSuspectView,
    ReconciliationStatusView,
    UnverifiedEntryView,
)

router = APIRouter(tags=["reconciliation"])


def get_reconcile(request: Request) -> Reconcile:
    return cast(Reconcile, request.app.state.reconcile)


def get_get_reconciliation_status(request: Request) -> GetReconciliationStatus:
    return cast(GetReconciliationStatus, request.app.state.get_reconciliation_status)


def get_list_unverified_entries(request: Request) -> ListUnverifiedEntries:
    return cast(ListUnverifiedEntries, request.app.state.list_unverified_entries)


def get_list_difference_suspects(request: Request) -> ListDifferenceSuspects:
    return cast(ListDifferenceSuspects, request.app.state.list_difference_suspects)


def _out(view: ReconciliationView) -> ReconcileOut:
    return ReconcileOut(
        id=view.id,
        through_entry_id=view.through_entry_id,
        system_total=view.system_total,
        counted_total=view.counted_total,
        difference=view.difference,
        matched=view.matched,
    )


@router.post("/reconciliations", status_code=201)
async def post_reconciliation(
    body: ReconcileRequest,
    user: Annotated[str, Depends(current_actor)],
    reconcile: Annotated[Reconcile, Depends(get_reconcile)],
) -> ReconcileOut:
    command = ReconcileCommand(
        counted_total=body.counted_total,
        note=body.note,
        counted=body.counted,
    )
    view = await reconcile(command, actor=user)
    return _out(view)


def _status_out(view: ReconciliationStatusView) -> ReconciliationStatusOut:
    return ReconciliationStatusOut(
        last_match_id=view.last_match_id,
        last_match_date=view.last_match_date,
        last_match_through_entry=view.last_match_through_entry,
        days_since_last_match=view.days_since_last_match,
        entries_since_last_match=view.entries_since_last_match,
        latest_attempt_matched=view.latest_attempt_matched,
        latest_difference=view.latest_difference,
    )


def _entry_out(view: UnverifiedEntryView) -> UnverifiedEntryOut:
    return UnverifiedEntryOut(
        id=view.id,
        tenure_id=view.tenure_id,
        kind=view.kind,
        occurred_on=view.occurred_on,
        recorded_at=view.recorded_at,
        recorded_by=view.recorded_by,
        note=view.note,
        tag=view.tag,
        cost_center_id=view.cost_center_id,
        member_id=view.member_id,
        reverses_id=view.reverses_id,
        is_voided=view.is_voided,
        net_effect=view.net_effect,
        size=view.size,
    )


def _suspect_out(view: DifferenceSuspectView) -> DifferenceSuspectOut:
    return DifferenceSuspectOut(
        entry_id=view.entry_id,
        kind=view.kind,
        occurred_on=view.occurred_on,
        effect=view.effect,
        note=view.note,
        why=view.why,
    )


@router.get("/reconciliation-status")
async def read_reconciliation_status(
    user: Annotated[str, Depends(current_actor)],
    get_status: Annotated[GetReconciliationStatus, Depends(get_get_reconciliation_status)],
) -> ReconciliationStatusOut:
    return _status_out(await get_status(actor=user))


@router.get("/unverified-entries")
async def read_unverified_entries(
    user: Annotated[str, Depends(current_actor)],
    list_unverified: Annotated[ListUnverifiedEntries, Depends(get_list_unverified_entries)],
) -> list[UnverifiedEntryOut]:
    return [_entry_out(view) for view in await list_unverified(actor=user)]


@router.get("/difference-suspects")
async def read_difference_suspects(
    difference: int,
    user: Annotated[str, Depends(current_actor)],
    list_suspects: Annotated[ListDifferenceSuspects, Depends(get_list_difference_suspects)],
    envelope_id: int | None = None,
) -> list[DifferenceSuspectOut]:
    views = await list_suspects(difference, envelope_id, actor=user)
    return [_suspect_out(view) for view in views]
