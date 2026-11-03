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
from mesl_finance.shared.api.responses import problem_responses

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


@router.post(
    "/reconciliations",
    status_code=201,
    summary="Record a screen-vs-notes check",
    responses=problem_responses(401, 409, 422),
)
async def post_reconciliation(
    body: ReconcileRequest,
    user: Annotated[str, Depends(current_actor)],
    reconcile: Annotated[Reconcile, Depends(get_reconcile)],
) -> ReconcileOut:
    """You counted what the lab actually holds; this stores it (B-20).

    `{counted_total, note="", counted={"<envelope_id>": int} | null}` —
    `reconcile` (SECURITY DEFINER, db/schema.sql:1047-1087) compares your
    counts with the system, stores the attempt and moves the review window
    forward when it MATCHES: before any match, every entry is unverified;
    after it, only what came later needs a look. Mismatches are stored too
    (difference ≠ 0 is the reviewer's point). The schema owns everything not
    typed: negative totals, unknown counted envelopes, `nothing to reconcile
    yet` → 409 with the rule's own message.
    """
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


@router.get(
    "/reconciliation-status",
    summary="Where the checks stand",
    responses=problem_responses(401),
)
async def read_reconciliation_status(
    user: Annotated[str, Depends(current_actor)],
    get_status: Annotated[GetReconciliationStatus, Depends(get_get_reconciliation_status)],
) -> ReconciliationStatusOut:
    """One row, always there: when the last MATCH was, how many entries and
    days have passed since, and what the LATEST attempt (matched or not) said.
    All last-match fields are null before any check (D-146 (3))."""
    return _status_out(await get_status(actor=user))


@router.get(
    "/unverified-entries",
    summary="Entries recorded since the last match",
    responses=problem_responses(401),
)
async def read_unverified_entries(
    user: Annotated[str, Depends(current_actor)],
    list_unverified: Annotated[ListUnverifiedEntries, Depends(get_list_unverified_entries)],
) -> list[UnverifiedEntryOut]:
    """The reviewer's queue (B-20): exactly what a match does NOT cover yet.

    The window is by ENTRY ID, not date — a late entry for an old date still
    shows (D-146 (4)). Each row is the `unverified_entries` view's 14 columns
    including `reverses_id` and `is_voided`, with `net_effect` and `size`.
    """
    return [_entry_out(view) for view in await list_unverified(actor=user)]


@router.get(
    "/difference-suspects",
    summary="Guess which entry explains a difference",
    responses=problem_responses(401, 422),
)
async def read_difference_suspects(
    difference: int,
    user: Annotated[str, Depends(current_actor)],
    list_suspects: Annotated[ListDifferenceSuspects, Depends(get_list_difference_suspects)],
    envelope_id: int | None = None,
) -> list[DifferenceSuspectOut]:
    """For a difference you cannot place: name candidates + WHY (D-146 (5)).

    `?difference=<your mismatch>` is called required; add optional
    `?envelope_id=` when you suspect one envelope. The heuristics — an extra
    zero, swapped digits, a single-sided transfer that exactly fills the gap
    — name `entry_id` + `effect` + `why`. No hits is `[]`, not an error.
    """
    views = await list_suspects(difference, envelope_id, actor=user)
    return [_suspect_out(view) for view in views]
