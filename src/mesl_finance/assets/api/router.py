from datetime import date
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Request

from mesl_finance.assets.api.schemas import (
    AssetActivityOut,
    AssetEventOut,
    AssetEventRequest,
    AssetOut,
    AssetStateOut,
    CreateAssetRequest,
    EditAssetRequest,
    FixEventOut,
    FixEventRequest,
    WhoHasWhatOut,
)
from mesl_finance.assets.application.create_asset import CreateAsset, CreateAssetCommand
from mesl_finance.assets.application.edit_asset import EditAsset, EditAssetCommand
from mesl_finance.assets.application.fix_event import FixAssetEvent, FixEventCommand
from mesl_finance.assets.application.list_asset_activity import ListAssetActivity
from mesl_finance.assets.application.list_assets import ListAssets
from mesl_finance.assets.application.read_asset_state import (
    ListAssetState,
    ListReplacementQueue,
    ListWhoHasWhat,
)
from mesl_finance.assets.application.record_event import RecordAssetEvent, RecordEventCommand
from mesl_finance.assets.domain.asset import AssetView
from mesl_finance.assets.domain.asset_activity import AssetActivityRow
from mesl_finance.assets.domain.asset_event import AssetEvent, AssetEventView
from mesl_finance.assets.domain.asset_reads import AssetStateRow, WhoHasWhatRow
from mesl_finance.auth.api.dependencies import current_actor

router = APIRouter(tags=["assets"])


def get_create_asset(request: Request) -> CreateAsset:
    return cast(CreateAsset, request.app.state.create_asset)


def get_list_assets(request: Request) -> ListAssets:
    return cast(ListAssets, request.app.state.list_assets)


def get_edit_asset(request: Request) -> EditAsset:
    return cast(EditAsset, request.app.state.edit_asset)


def get_record_asset_event(request: Request) -> RecordAssetEvent:
    return cast(RecordAssetEvent, request.app.state.record_asset_event)


def get_fix_asset_event(request: Request) -> FixAssetEvent:
    return cast(FixAssetEvent, request.app.state.fix_asset_event)


def get_list_asset_activity(request: Request) -> ListAssetActivity:
    return cast(ListAssetActivity, request.app.state.list_asset_activity)


def get_list_asset_state(request: Request) -> ListAssetState:
    return cast(ListAssetState, request.app.state.list_asset_state)


def get_list_who_has_what(request: Request) -> ListWhoHasWhat:
    return cast(ListWhoHasWhat, request.app.state.list_who_has_what)


def get_list_replacement_queue(request: Request) -> ListReplacementQueue:
    return cast(ListReplacementQueue, request.app.state.list_replacement_queue)


def _activity_out(row: AssetActivityRow) -> AssetActivityOut:
    return AssetActivityOut(
        asset_name=row.asset_name,
        ownership=row.ownership,
        kind=row.kind,
        source=row.source,
        units=row.units,
        events=row.events,
    )


def _state_out(row: AssetStateRow) -> AssetStateOut:
    return AssetStateOut(
        asset_id=row.asset_id,
        asset_name=row.asset_name,
        ownership=row.ownership,
        mode=row.mode,
        tag=row.tag,
        stock=row.stock,
        damaged=row.damaged,
        with_members=row.with_members,
        lost=row.lost,
        scrapped=row.scrapped,
        exchanged=row.exchanged,
    )


def _holding_out(row: WhoHasWhatRow) -> WhoHasWhatOut:
    return WhoHasWhatOut(
        asset_id=row.asset_id,
        asset_name=row.asset_name,
        member_id=row.member_id,
        member_name=row.member_name,
        quantity=row.quantity,
    )


def _asset_out(view: AssetView) -> AssetOut:
    return AssetOut(
        id=view.id,
        name=view.name,
        mode=view.mode,
        ownership=view.ownership,
        tag=view.tag,
        note=view.note,
    )


def _event_out(view: AssetEventView) -> AssetEventOut:
    return AssetEventOut(
        id=view.id,
        asset_id=view.asset_id,
        kind=view.kind,
        quantity=view.quantity,
        occurred_on=view.occurred_on,
        note=view.note,
    )


def _unknown(asset_id: int) -> HTTPException:
    return HTTPException(status_code=404, detail=f"asset {asset_id} does not exist")


@router.post("/assets", status_code=201)
async def post_asset(
    body: CreateAssetRequest,
    user: Annotated[str, Depends(current_actor)],
    create_asset: Annotated[CreateAsset, Depends(get_create_asset)],
) -> AssetOut:
    command = CreateAssetCommand(
        name=body.name,
        mode=body.mode.value,
        ownership=body.ownership.value,
        tag=body.tag,
        note=body.note,
    )
    return _asset_out(await create_asset(command, actor=user))


@router.get("/assets")
async def get_assets(
    user: Annotated[str, Depends(current_actor)],
    list_assets: Annotated[ListAssets, Depends(get_list_assets)],
) -> list[AssetOut]:
    views = await list_assets(actor=user)
    return [_asset_out(view) for view in views]


@router.post("/assets/{asset_id}/edit")
async def post_edit(
    asset_id: int,
    body: EditAssetRequest,
    user: Annotated[str, Depends(current_actor)],
    edit_asset: Annotated[EditAsset, Depends(get_edit_asset)],
) -> AssetOut:
    command = EditAssetCommand(
        fields=frozenset(body.model_fields_set),
        name=body.name,
        tag=body.tag,
        note=body.note,
        mode=None if body.mode is None else body.mode.value,
        ownership=None if body.ownership is None else body.ownership.value,
    )
    view = await edit_asset(asset_id, command, actor=user)
    if view is None:
        raise _unknown(asset_id)
    return _asset_out(view)


@router.post("/assets/{asset_id}/events", status_code=201)
async def post_event(
    asset_id: int,
    body: AssetEventRequest,
    user: Annotated[str, Depends(current_actor)],
    record_asset_event: Annotated[RecordAssetEvent, Depends(get_record_asset_event)],
) -> AssetEventOut:
    # The kind shapes are the app's 422 `validation_failed` refusals (Q5=a):
    # validated here, before any transaction opens.
    AssetEvent.create(
        kind=body.kind.value,
        quantity=body.quantity,
        occurred_on=body.occurred_on,
        member_id=body.member_id,
        source=None if body.source is None else body.source.value,
        ledger_transaction_id=body.ledger_transaction_id,
        note=body.note,
    )
    command = RecordEventCommand(
        asset_id=asset_id,
        kind=body.kind.value,
        quantity=body.quantity,
        occurred_on=body.occurred_on,
        member_id=body.member_id,
        source=None if body.source is None else body.source.value,
        ledger_transaction_id=body.ledger_transaction_id,
        note=body.note,
    )
    view = await record_asset_event(command, actor=user)
    if view is None:
        raise _unknown(asset_id)
    return _event_out(view)


@router.post("/assets/{asset_id}/events/{event_id}/fix", status_code=201)
async def post_fix_event(
    asset_id: int,
    event_id: int,
    body: FixEventRequest,
    user: Annotated[str, Depends(current_actor)],
    fix_asset_event: Annotated[FixAssetEvent, Depends(get_fix_asset_event)],
) -> FixEventOut:
    command = FixEventCommand(
        asset_id=asset_id,
        event_id=event_id,
        quantity=body.quantity,
        occurred_on=body.occurred_on,
        note=body.note,
    )
    answer = await fix_asset_event(command, actor=user)
    if answer is None:
        # The URL identifies the resource: the detail names both ids, so an
        # unknown asset and an unknown event are told apart by the caller.
        raise HTTPException(
            status_code=404, detail=f"event {event_id} does not exist under asset {asset_id}"
        )
    view, reversal_id = answer
    return FixEventOut(
        id=view.id,
        asset_id=view.asset_id,
        kind=view.kind,
        quantity=view.quantity,
        occurred_on=view.occurred_on,
        note=view.note,
        reversal_id=reversal_id,
    )


@router.get("/assets/state")
async def get_asset_state(
    user: Annotated[str, Depends(current_actor)],
    list_asset_state: Annotated[ListAssetState, Depends(get_list_asset_state)],
) -> list[AssetStateOut]:
    rows = await list_asset_state(actor=user)
    return [_state_out(row) for row in rows]


@router.get("/assets/holdings")
async def get_asset_holdings(
    user: Annotated[str, Depends(current_actor)],
    list_who_has_what: Annotated[ListWhoHasWhat, Depends(get_list_who_has_what)],
) -> list[WhoHasWhatOut]:
    rows = await list_who_has_what(actor=user)
    return [_holding_out(row) for row in rows]


@router.get("/assets/replacement-queue")
async def get_replacement_queue(
    user: Annotated[str, Depends(current_actor)],
    list_replacement_queue: Annotated[ListReplacementQueue, Depends(get_list_replacement_queue)],
) -> list[AssetStateOut]:
    rows = await list_replacement_queue(actor=user)
    return [_state_out(row) for row in rows]


@router.get("/assets/activity")
async def get_asset_activity(
    from_date: date,
    to_date: date,
    user: Annotated[str, Depends(current_actor)],
    list_asset_activity: Annotated[ListAssetActivity, Depends(get_list_asset_activity)],
) -> list[AssetActivityOut]:
    rows = await list_asset_activity(from_date, to_date, actor=user)
    return [_activity_out(row) for row in rows]
