from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Registration(BaseModel):
    model_config = ConfigDict(extra="allow")

    project_reg_id: int
    project_reg_no: str | None = None
    project_ack_no: str | None = None
    project_name: str | None = None
    project_type: str | None = None
    project_status: str | None = None
    start_date: str | None = None
    original_end_date: str | None = None
    extended_end_date: str | None = None
    approved_on: str | None = None
    has_extension: bool = False
    certificate_uid: str | None = None
    certificate_download_url: str | None = None
    wfo_id: str | None = None
    last_updated_on: str | None = None


class Promoter(BaseModel):
    model_config = ConfigDict(extra="allow")

    promoter_id: int | None = None
    name: str | None = None
    type: str | None = None
    email_id: str | None = None
    mobile_no: str | None = None
    address: str | None = None
    taluka_name: str | None = None
    pan_no_masked: str | None = None
    company_reg_no: str | None = None
    registration_certificate_uid: str | None = None
    registration_certificate_download_url: str | None = None


class Financials(BaseModel):
    total_project_cost: float | None = None
    registration_fee: float | None = None
    payment_status: str | None = None
    min_unit_cost: float | None = None
    max_unit_cost: float | None = None
    total_units: int | None = None
    inventory_by_block: list[dict[str, Any]] = Field(default_factory=list)


class QuarterlyTrendPoint(BaseModel):
    quarter_name: str | None = None
    progress_pct: float | None = None


class Progress(BaseModel):
    score: float | None = None
    label: str | None = None
    arch_score: float | None = None
    engg_score: float | None = None
    time_laps_ratio: float | None = None
    quarterly_trend: list[QuarterlyTrendPoint] = Field(default_factory=list)


class BlockConstructionPhases(BaseModel):
    excavation: dict[str, Any] = Field(default_factory=dict)
    plinth: dict[str, Any] = Field(default_factory=dict)
    podium: dict[str, Any] = Field(default_factory=dict)
    stilt: dict[str, Any] = Field(default_factory=dict)
    slab: dict[str, Any] = Field(default_factory=dict)
    internal: dict[str, Any] = Field(default_factory=dict)
    sanitary: dict[str, Any] = Field(default_factory=dict)
    staircase: dict[str, Any] = Field(default_factory=dict)
    external: dict[str, Any] = Field(default_factory=dict)
    installation: dict[str, Any] = Field(default_factory=dict)
    common: dict[str, Any] = Field(default_factory=dict)


class BlockDetail(BaseModel):
    model_config = ConfigDict(extra="allow")

    block_id: int | None = None
    block_name: str | None = None
    dev_start_date: str | None = None
    dev_end_date: str | None = None
    height_meters: float | None = None
    fsi: float | None = None
    commencement_cert_no: str | None = None
    commencement_certificate_uid: str | None = None
    commencement_certificate_download_url: str | None = None
    units_booked: int | None = None
    units_unbooked: int | None = None
    booking_pct: float | None = None
    block_progress_pct: float | None = None
    construction_phases: BlockConstructionPhases = Field(
        default_factory=BlockConstructionPhases
    )


class UnitsSummary(BaseModel):
    total_units: int | None = None
    min_cost: float | None = None
    max_cost: float | None = None
    total_carpet_area_sqm: float | None = None
    min_carpet_area_sqm: float | None = None
    max_carpet_area_sqm: float | None = None
    average_unit_size_sqm: float | None = None


class InventoryUnit(BaseModel):
    model_config = ConfigDict(extra="allow")

    flat_no: str | None = None
    block_name: str | None = None
    usage: str | None = None
    carpet_area_sqm: float | None = None
    balcony_area_sqm: float | None = None
    unit_status: str | None = None
    unit_consideration: float | None = None
    received_amount: float | None = None
    balance_amount: float | None = None
    allottee_name: str | None = None
    type_of_kyc: str | None = None
    kyc_id: str | None = None
    mobile_number: str | None = None
    encumbrance_status: str | None = None
    date_of_agreement: str | None = None


class QuarterSummary(BaseModel):
    model_config = ConfigDict(extra="allow")

    quarter_id: int | None = None
    quarter_name: str | None = None
    qtr_index: int | None = None
    start_date: str | None = None
    end_date: str | None = None
    extended_date: str | None = None
    payment_status: str | None = None
    status: str | None = None
    submitted_on: str | None = None


class Location(BaseModel):
    address: str | None = None
    district: str | None = None
    taluka: str | None = None
    coordinates: list[dict[str, float]] = Field(default_factory=list)
    process_type: str | None = None


class ApplicationRecord(BaseModel):
    application_number: str | None = None
    approval_date: str | None = None
    type: str | None = None


class BankAccount(BaseModel):
    model_config = ConfigDict(extra="allow")

    bank_name: str | None = None
    branch_name: str | None = None
    ifsc_code: str | None = None
    account_number: str | None = None
    account_name: str | None = None
    opening_date: str | None = None
    closing_date: str | None = None
    opening_balance: float | None = None
    closing_balance: float | None = None
    status: str | None = None


class BankAccounts(BaseModel):
    collection_account: BankAccount | None = None
    retention_account: BankAccount | None = None


class AnnualAuditRecord(BaseModel):
    financial_year: str | None = None
    status: str | None = None
    submitted_on: str | None = None
    pdf_uid: str | None = None
    pdf_download_url: str | None = None


class ProjectDetail(BaseModel):
    registration: Registration
    promoter: Promoter
    financials: Financials
    progress: Progress
    blocks: list[BlockDetail] = Field(default_factory=list)
    units_summary: UnitsSummary = Field(default_factory=UnitsSummary)
    inventory: list[InventoryUnit] = Field(default_factory=list)
    quarters: list[QuarterSummary] = Field(default_factory=list)
    construction_timeline: list[dict[str, Any]] = Field(default_factory=list)
    location: Location = Field(default_factory=Location)
    applications: list[ApplicationRecord] = Field(default_factory=list)
    bank_accounts: BankAccounts = Field(default_factory=BankAccounts)
    annual_audits: list[AnnualAuditRecord] = Field(default_factory=list)
    documents: dict[str, Any] = Field(default_factory=dict)
    professionals: dict[str, Any] = Field(default_factory=dict)


class InventoryResponse(BaseModel):
    project_reg_id: int
    form_three_id: int | None = None
    inventory: list[InventoryUnit] = Field(default_factory=list)


class QuartersResponse(BaseModel):
    project_reg_id: int
    quarters: list[QuarterSummary] = Field(default_factory=list)
    quarterly_trend: list[QuarterlyTrendPoint] = Field(default_factory=list)


class QuarterDetail(BaseModel):
    project_reg_id: int
    quarter_id: int
    quarter_name: str | None = None
    qtr_index: int | None = None
    start_date: str | None = None
    end_date: str | None = None
    extended_date: str | None = None
    payment_status: str | None = None
    status: str | None = None
    submitted_on: str | None = None
    progress_pct: float | None = None
    delta_from_previous_pct: float | None = None
    enquiry_open: bool | None = None
    public_documents: dict[str, Any] = Field(default_factory=dict)
