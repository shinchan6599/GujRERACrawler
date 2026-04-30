from fastapi import APIRouter, Depends, HTTPException, Request

from app.client import GujReraClient
from app.gujrera.aggregator import (
    get_quarter_detail,
    ProjectNotFoundError,
    get_inventory_only,
    get_project_detail,
    get_quarters_only,
)
from app.gujrera.listing import find_project_listing_entry
from app.schemas.project import InventoryResponse, ProjectDetail, QuarterDetail, QuartersResponse

router = APIRouter(prefix="/api/projects", tags=["projects"])


def get_client(request: Request) -> GujReraClient:
    return request.app.state.gujrera_client


@router.get("/{project_reg_id}", response_model=ProjectDetail)
async def project_detail(
    project_reg_id: int,
    client: GujReraClient = Depends(get_client),
) -> ProjectDetail:
    listing_entry = await find_project_listing_entry(client, project_reg_id)
    try:
        return await get_project_detail(client, project_reg_id, listing_entry)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Project {exc.args[0]} not found") from exc


@router.get("/{project_reg_id}/inventory", response_model=InventoryResponse)
async def project_inventory(
    project_reg_id: int,
    client: GujReraClient = Depends(get_client),
) -> InventoryResponse:
    try:
        return await get_inventory_only(client, project_reg_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Project {exc.args[0]} not found") from exc


@router.get("/{project_reg_id}/quarters", response_model=QuartersResponse)
async def project_quarters(
    project_reg_id: int,
    client: GujReraClient = Depends(get_client),
) -> QuartersResponse:
    try:
        return await get_quarters_only(client, project_reg_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Project {exc.args[0]} not found") from exc


@router.get("/{project_reg_id}/quarters/{quarter_id}", response_model=QuarterDetail)
async def project_quarter_detail(
    project_reg_id: int,
    quarter_id: int,
    client: GujReraClient = Depends(get_client),
) -> QuarterDetail:
    try:
        return await get_quarter_detail(client, project_reg_id, quarter_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Project {exc.args[0]} not found") from exc
