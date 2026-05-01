from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

import structlog

from app.client import GujReraClient
from app.config import Settings
from app.db.store import LocalStore
from app.gujrera.aggregator import ProjectNotFoundError, get_project_detail
from app.gujrera.listing import fetch_project_listing_raw, transform_project_summary


logger = structlog.get_logger("local_sync")


async def sync_projects_to_local_store(
    *,
    client: GujReraClient,
    store: LocalStore,
    settings: Settings,
    run_id: int,
    limit: int | None = None,
    offset: int = 0,
    concurrency: int | None = None,
) -> None:
    listing_payload = await fetch_project_listing_raw(client)
    selected_listing = listing_payload[offset : offset + limit] if limit else listing_payload[offset:]
    summaries = [transform_project_summary(item).model_dump(mode="json") for item in selected_listing]
    semaphore = asyncio.Semaphore(concurrency or settings.local_sync_concurrency)
    synced_projects = 0
    failed_projects = 0

    async def sync_one(raw_item: dict[str, Any], summary: dict[str, Any]) -> tuple[bool, int]:
        project_reg_id = raw_item["projectRegId"]
        async with semaphore:
            try:
                detail = await get_project_detail(client, project_reg_id, raw_item)
                await store.upsert_project_bundle(summary, detail)
                return True, project_reg_id
            except ProjectNotFoundError:
                logger.warning("local_sync_project_not_found", project_reg_id=project_reg_id)
                return False, project_reg_id
            except Exception as exc:  # pragma: no cover - network heavy
                logger.warning(
                    "local_sync_project_failed",
                    project_reg_id=project_reg_id,
                    error=str(exc),
                )
                return False, project_reg_id

    tasks = [
        asyncio.create_task(sync_one(raw_item, summary))
        for raw_item, summary in zip(selected_listing, summaries)
    ]
    try:
        for task in asyncio.as_completed(tasks):
            ok, _project_reg_id = await task
            if ok:
                synced_projects += 1
            else:
                failed_projects += 1
            await store.update_sync_run_progress(
                run_id,
                synced_projects=synced_projects,
                failed_projects=failed_projects,
            )
        await store.complete_sync_run(
            run_id,
            synced_projects=synced_projects,
            failed_projects=failed_projects,
        )
    except Exception as exc:  # pragma: no cover - background path
        for task in tasks:
            if not task.done():
                task.cancel()
        await store.fail_sync_run(
            run_id,
            synced_projects=synced_projects,
            failed_projects=failed_projects,
            error_message=str(exc),
        )
        raise
