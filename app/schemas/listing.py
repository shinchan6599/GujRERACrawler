from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DistrictSummaryStat(BaseModel):
    model_config = ConfigDict(extra="allow")

    project_type: str | None = None
    total: int | None = None
    counts: dict[str, int] = Field(default_factory=dict)


class ProjectSummary(BaseModel):
    model_config = ConfigDict(extra="allow")

    project_reg_id: int
    project_name: str
    reg_no: str | None = None
    district_name: str | None = None
    district_type: str | None = None
    project_type: str | None = None
    project_status: str | None = None
    promoter_name: str | None = None
    project_address: str | None = None
    promoter_address: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    extended_end_date: str | None = None
    approved_on: str | None = None
    project_cost: float | None = None
    registration_fee: float | None = None
    payment_status: str | None = None
    wfo_id: str | None = None
class ListingResponse(BaseModel):
    summary_stats: list[DistrictSummaryStat] = Field(default_factory=list)
    total_projects: int
    filtered_projects: int
    projects: list[ProjectSummary] = Field(default_factory=list)
