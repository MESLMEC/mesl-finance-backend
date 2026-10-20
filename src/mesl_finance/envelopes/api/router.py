from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Request

from mesl_finance.auth.api.dependencies import current_actor
from mesl_finance.envelopes.api.schemas import (
    CreateEnvelopeRequest,
    EnvelopeOut,
    EnvelopeSettingsRequest,
    RenameEnvelopeRequest,
)
from mesl_finance.envelopes.application.create_envelope import (
    CreateEnvelope,
    CreateEnvelopeCommand,
)
from mesl_finance.envelopes.application.deactivate_envelope import DeactivateEnvelope
from mesl_finance.envelopes.application.list_envelopes import ListEnvelopes
from mesl_finance.envelopes.application.rename_envelope import RenameEnvelope
from mesl_finance.envelopes.application.update_envelope_settings import UpdateEnvelopeSettings
from mesl_finance.envelopes.domain.envelope import EnvelopeView

router = APIRouter(tags=["envelopes"])


def get_create_envelope(request: Request) -> CreateEnvelope:
    return cast(CreateEnvelope, request.app.state.create_envelope)


def get_list_envelopes(request: Request) -> ListEnvelopes:
    return cast(ListEnvelopes, request.app.state.list_envelopes)


def get_rename_envelope(request: Request) -> RenameEnvelope:
    return cast(RenameEnvelope, request.app.state.rename_envelope)


def get_update_envelope_settings(request: Request) -> UpdateEnvelopeSettings:
    return cast(UpdateEnvelopeSettings, request.app.state.update_envelope_settings)


def get_deactivate_envelope(request: Request) -> DeactivateEnvelope:
    return cast(DeactivateEnvelope, request.app.state.deactivate_envelope)


def _out(view: EnvelopeView) -> EnvelopeOut:
    return EnvelopeOut(
        id=view.id,
        name=view.name,
        target_cap=view.target_cap,
        alloc_priority=view.alloc_priority,
        is_pool=view.is_pool,
        active=view.active,
    )


def _found(view: EnvelopeView | None, envelope_id: int) -> EnvelopeView:
    if view is None:
        raise HTTPException(status_code=404, detail=f"envelope {envelope_id} does not exist")
    return view


@router.post("/envelopes", status_code=201)
async def post_envelope(
    body: CreateEnvelopeRequest,
    user: Annotated[str, Depends(current_actor)],
    create_envelope: Annotated[CreateEnvelope, Depends(get_create_envelope)],
) -> EnvelopeOut:
    view = await create_envelope(CreateEnvelopeCommand(**body.model_dump()), actor=user)
    return _out(view)


@router.get("/envelopes")
async def get_envelopes(
    user: Annotated[str, Depends(current_actor)],
    list_envelopes: Annotated[ListEnvelopes, Depends(get_list_envelopes)],
) -> list[EnvelopeOut]:
    return [_out(view) for view in await list_envelopes(actor=user)]


@router.post("/envelopes/{envelope_id}/rename")
async def post_rename(
    envelope_id: int,
    body: RenameEnvelopeRequest,
    user: Annotated[str, Depends(current_actor)],
    rename_envelope: Annotated[RenameEnvelope, Depends(get_rename_envelope)],
) -> EnvelopeOut:
    view = await rename_envelope(envelope_id, body.name, actor=user)
    return _out(_found(view, envelope_id))


@router.post("/envelopes/{envelope_id}/settings")
async def post_settings(
    envelope_id: int,
    body: EnvelopeSettingsRequest,
    user: Annotated[str, Depends(current_actor)],
    update_settings: Annotated[UpdateEnvelopeSettings, Depends(get_update_envelope_settings)],
) -> EnvelopeOut:
    view = await update_settings(envelope_id, body.target_cap, body.alloc_priority, actor=user)
    return _out(_found(view, envelope_id))


@router.post("/envelopes/{envelope_id}/deactivate")
async def post_deactivate(
    envelope_id: int,
    user: Annotated[str, Depends(current_actor)],
    deactivate_envelope: Annotated[DeactivateEnvelope, Depends(get_deactivate_envelope)],
) -> EnvelopeOut:
    view = await deactivate_envelope(envelope_id, actor=user)
    return _out(_found(view, envelope_id))
