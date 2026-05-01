from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SyncRequest(BaseModel):
    limit: int | None = None
    offset: int = 0
    concurrency: int | None = None


class SyncRunStatus(BaseModel):
    id: int
    status: str
    total_projects: int | None = None
    synced_projects: int = 0
    failed_projects: int = 0
    limit_value: int | None = None
    offset_value: int = 0
    started_at: str
    finished_at: str | None = None
    error_message: str | None = None


class StorageSummary(BaseModel):
    db_path: str
    project_count: int
    block_count: int
    quarter_count: int
    inventory_count: int
    rag_chunk_count: int
    last_sync_run: dict[str, Any] | None = None
