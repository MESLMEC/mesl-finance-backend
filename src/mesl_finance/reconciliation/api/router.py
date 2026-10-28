"""Route for the reconciliation action (ROADMAP 10.1)."""

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request

from mesl_finance.auth.api.dependencies import current_actor
from mesl_finance.reconciliation.api.schemas import ReconcileOut, ReconcileRequest
from mesl_finance.reconciliation.application.reconcile import Reconcile, ReconcileCommand
from mesl_finance.reconciliation.domain.reconciliation import ReconciliationView

router = APIRouter(tags=["reconciliation"])


def get_reconcile(request: Request) -> Reconcile:
    return cast(Reconcile, request.app.state.reconcile)


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
