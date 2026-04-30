from __future__ import annotations

import asyncio

from cachetools import TTLCache

from app.client import GujReraClient
from app.config import get_settings
from app.schemas.listing import DistrictSummaryStat, ProjectSummary
from app.utils.transforms import (
    clean_text,
    normalize_date,
    normalize_payment_status,
    parse_float,
    parse_int,
    unwrap_data,
)

_settings = get_settings()
_listing_cache: TTLCache[str, list[dict]] = TTLCache(maxsize=1, ttl=_settings.listing_cache_ttl_seconds)
_summary_cache: TTLCache[str, list[dict]] = TTLCache(maxsize=1, ttl=_settings.listing_cache_ttl_seconds)
_cache_lock = asyncio.Lock()


async def fetch_summary_stats(client: GujReraClient) -> list[dict]:
    async with _cache_lock:
        cached = _summary_cache.get("summary_stats")
        if cached is not None:
            return cached
    payload = await client.get_json(
        "/dashboard/get-district-wise-projects/0/0/all/Gujarat",
        endpoint_name="L1_summary_stats",
    )
    data = unwrap_data(payload) or []
    async with _cache_lock:
        _summary_cache["summary_stats"] = data
    return data


async def fetch_project_listing_raw(client: GujReraClient) -> list[dict]:
    async with _cache_lock:
        cached = _listing_cache.get("project_listing")
        if cached is not None:
            return cached
    payload = await client.get_json(
        "/dashboard/get-district-wise-projectlist/0/0/all/all/all",
        endpoint_name="L2_project_listing",
    )
    data = unwrap_data(payload) or []
    async with _cache_lock:
        _listing_cache["project_listing"] = data
    return data


def transform_summary_stats(items: list[dict]) -> list[DistrictSummaryStat]:
    stats: list[DistrictSummaryStat] = []
    for item in items:
        counts = {
            key: parse_int(value) or 0
            for key, value in item.items()
            if key not in {"type", "total"}
        }
        stats.append(
            DistrictSummaryStat(
                project_type=clean_text(item.get("type")),
                total=parse_int(item.get("total")),
                counts=counts,
            )
        )
    return stats


def transform_project_summary(item: dict) -> ProjectSummary:
    return ProjectSummary(
        project_reg_id=item["projectRegId"],
        project_name=item.get("projectName") or "Unknown Project",
        reg_no=clean_text(item.get("regNo")),
        district_name=clean_text(item.get("districtName")),
        district_type=clean_text(item.get("districtType")),
        project_type=clean_text(item.get("projectType")),
        project_status=clean_text(item.get("project_status")),
        promoter_name=clean_text(item.get("promoterName")),
        project_address=clean_text(item.get("project_address")),
        promoter_address=clean_text(item.get("promoterAddress")),
        start_date=normalize_date(item.get("startDate")),
        end_date=normalize_date(item.get("endDate")),
        extended_end_date=normalize_date(item.get("extDate")),
        approved_on=normalize_date(item.get("approvedOn")),
        project_cost=parse_float(item.get("projectCost") or item.get("total_est_cost_of_proj")),
        registration_fee=parse_float(item.get("regFee")),
        payment_status=normalize_payment_status(item.get("payment_status")),
        wfo_id=clean_text(item.get("wfoid")),
    )


async def find_project_listing_entry(
    client: GujReraClient, project_reg_id: int
) -> dict | None:
    projects = await fetch_project_listing_raw(client)
    for item in projects:
        if item.get("projectRegId") == project_reg_id:
            return item
    return None
