import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request

from app.client import GujReraClient
from app.config import Settings, get_settings
from app.db.store import LocalStore
from app.db.sync import sync_projects_to_local_store
from app.gujrera.listing import fetch_project_listing_raw
from app.schemas.storage import StorageSummary, SyncRequest, SyncRunStatus

router = APIRouter(prefix="/api/storage", tags=["storage"])


def get_client(request: Request) -> GujReraClient:
    return request.app.state.gujrera_client


def get_store(request: Request) -> LocalStore:
    return request.app.state.local_store


@router.get("/summary", response_model=StorageSummary)
async def storage_summary(store: LocalStore = Depends(get_store)) -> StorageSummary:
    return StorageSummary(**(await store.get_storage_summary()))


@router.post("/sync", response_model=SyncRunStatus)
async def start_sync(
    payload: SyncRequest,
    request: Request,
    client: GujReraClient = Depends(get_client),
    store: LocalStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
) -> SyncRunStatus:
    all_projects = await fetch_project_listing_raw(client)
    total_projects = len(all_projects[payload.offset : payload.offset + payload.limit]) if payload.limit else max(0, len(all_projects) - payload.offset)
    run_id = await store.create_sync_run(
        total_projects=total_projects,
        limit_value=payload.limit,
        offset_value=payload.offset,
    )
    task = asyncio.create_task(
        sync_projects_to_local_store(
            client=client,
            store=store,
            settings=settings,
            run_id=run_id,
            limit=payload.limit,
            offset=payload.offset,
            concurrency=payload.concurrency,
        )
    )
    request.app.state.sync_tasks[run_id] = task
    return SyncRunStatus(**(await store.get_sync_run(run_id)))


@router.get("/runs/{run_id}", response_model=SyncRunStatus)
async def get_sync_run_status(
    run_id: int,
    store: LocalStore = Depends(get_store),
) -> SyncRunStatus:
    status = await store.get_sync_run(run_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Sync run {run_id} not found")
    return SyncRunStatus(**status)
