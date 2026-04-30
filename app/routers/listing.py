import asyncio

from fastapi import APIRouter, Depends, Query, Request

from app.client import GujReraClient
from app.gujrera.listing import (
    fetch_project_listing_raw,
    fetch_summary_stats,
    transform_project_summary,
    transform_summary_stats,
)
from app.schemas.listing import ListingResponse

router = APIRouter(prefix="/api/projects", tags=["projects"])


def get_client(request: Request) -> GujReraClient:
    return request.app.state.gujrera_client


@router.get("", response_model=ListingResponse)
async def list_projects(
    district: str | None = Query(default=None),
    project_type: str | None = Query(default=None),
    project_status: str | None = Query(default=None),
    q: str | None = Query(default=None, description="Search by project or promoter name"),
    client: GujReraClient = Depends(get_client),
) -> ListingResponse:
    summary_payload, listing_payload = await asyncio.gather(
        fetch_summary_stats(client),
        fetch_project_listing_raw(client),
    )
    stats = transform_summary_stats(summary_payload)
    projects = [transform_project_summary(item) for item in listing_payload]

    if district:
        district_fold = district.casefold()
        projects = [
            item
            for item in projects
            if (item.district_name or "").casefold() == district_fold
            or (item.district_type or "").casefold() == district_fold
        ]
    if project_type:
        type_fold = project_type.casefold()
        projects = [
            item
            for item in projects
            if (item.project_type or "").casefold() == type_fold
        ]
    if project_status:
        status_fold = project_status.casefold()
        projects = [
            item
            for item in projects
            if (item.project_status or "").casefold() == status_fold
        ]
    if q:
        needle = q.casefold()
        projects = [
            item
            for item in projects
            if needle in (item.project_name or "").casefold()
            or needle in (item.promoter_name or "").casefold()
            or needle in (item.reg_no or "").casefold()
        ]

    return ListingResponse(
        summary_stats=stats,
        total_projects=len(listing_payload),
        filtered_projects=len(projects),
        projects=projects,
    )
