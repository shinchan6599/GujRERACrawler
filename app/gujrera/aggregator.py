from __future__ import annotations

import asyncio
from typing import Any

from app.client import GujReraClient
from app.gujrera.detail.blocks import (
    fetch_block_chart,
    fetch_block_list,
    fetch_progress_report,
    fetch_qpr_details,
    fetch_unit_details,
)
from app.gujrera.detail.core import (
    fetch_all_data,
    fetch_applications,
    fetch_collection_account,
    fetch_documents,
    fetch_prev_project_list,
    fetch_project_people,
    fetch_promoter,
    fetch_retention_account,
)
from app.gujrera.detail.forms import fetch_construction_timeline, fetch_inventory
from app.gujrera.detail.misc import fetch_block_progress, fetch_form5, fetch_geo
from app.gujrera.detail.quarters import (
    fetch_public_quarter_forms,
    fetch_progress_trend,
    fetch_quarter_enquiry_status,
    fetch_qtr_form_ids,
    fetch_quarters,
)
from app.schemas.project import (
    AnnualAuditRecord,
    ApplicationRecord,
    BankAccount,
    BankAccounts,
    BlockConstructionPhases,
    BlockDetail,
    Financials,
    InventoryResponse,
    InventoryUnit,
    Location,
    Progress,
    ProjectDetail,
    Promoter,
    QuarterDetail,
    QuarterSummary,
    QuartersResponse,
    QuarterlyTrendPoint,
    Registration,
    UnitsSummary,
)
from app.utils.transforms import (
    clean_text,
    coalesce,
    download_url,
    ensure_list,
    map_coordinates,
    normalize_date,
    normalize_datetime,
    normalize_payment_status,
    parse_float,
    parse_int,
    unwrap_data,
)


class ProjectNotFoundError(Exception):
    pass


def _safe_payload(result: Any) -> Any:
    if isinstance(result, Exception):
        return None
    return unwrap_data(result)


def _first_matching_project(prev_project_payload: dict | None, project_reg_id: int) -> dict:
    if not isinstance(prev_project_payload, dict):
        return {}
    records = ensure_list(prev_project_payload.get("gujrera"))
    for record in records:
        if record.get("projectRegId") == project_reg_id:
            return record
    return records[0] if records else {}


def _timeline_phases(item: dict) -> BlockConstructionPhases:
    def phase(name: str) -> dict[str, Any]:
        return {
            "planned_start": normalize_date(item.get(f"{name}StartDate")),
            "planned_end": normalize_date(item.get(f"{name}EndDate")),
            "actual_start": normalize_date(item.get(f"{name}ActStartDate")),
            "actual_end": normalize_date(item.get(f"{name}ActEndDate")),
            "work_done_pct": parse_float(item.get(f"{name}WrokDone") or item.get(f"{name}WorkDone")),
        }

    return BlockConstructionPhases(
        excavation=phase("excavation"),
        plinth=phase("plinth"),
        podium=phase("podium"),
        stilt=phase("still"),
        slab=phase("slab"),
        internal=phase("internal"),
        sanitary=phase("sanitary"),
        staircase=phase("staircase"),
        external=phase("external"),
        installation=phase("installation"),
        common=phase("common"),
    )


def _transform_bank_account(payload: dict | None) -> BankAccount | None:
    if not isinstance(payload, dict) or not payload:
        return None
    return BankAccount(
        bank_name=clean_text(payload.get("bankName")),
        branch_name=clean_text(payload.get("branchName")),
        ifsc_code=clean_text(payload.get("ifscCode")),
        account_number=clean_text(payload.get("accountNumber")),
        account_name=clean_text(payload.get("accountName")),
        opening_date=normalize_date(payload.get("openingDate")),
        closing_date=normalize_date(payload.get("closingDate")),
        opening_balance=parse_float(payload.get("openingBal")),
        closing_balance=parse_float(payload.get("closingBal")),
        status=clean_text(payload.get("status")),
    )


def _transform_inventory(payload: dict | None) -> tuple[int | None, list[InventoryUnit]]:
    if isinstance(payload, list):
        form_three_id = None
        items = payload
    elif isinstance(payload, dict):
        form_three_id = parse_int(payload.get("formThreeId"))
        items = ensure_list(payload.get("formThreeAList") or payload.get("data"))
    else:
        return None, []
    return form_three_id, [
        InventoryUnit(
            flat_no=clean_text(item.get("flatNo")),
            block_name=clean_text(item.get("blockName")),
            usage=clean_text(item.get("usage")),
            carpet_area_sqm=parse_float(item.get("carpetArea")),
            balcony_area_sqm=parse_float(item.get("areaofExBalcony")),
            unit_status=clean_text(item.get("status")),
            unit_consideration=parse_float(item.get("unitConsideration")),
            received_amount=parse_float(item.get("receivedAmount")),
            balance_amount=parse_float(item.get("balanceAmount")),
            allottee_name=clean_text(item.get("alloteeName")),
            type_of_kyc=clean_text(item.get("typeofKYC")),
            kyc_id=clean_text(item.get("kycid") or item.get("kycId")),
            mobile_number=clean_text(item.get("mobileNumber")),
            encumbrance_status=clean_text(item.get("encumbranceStatus")),
            date_of_agreement=normalize_date(item.get("dateOfAgrrement")),
        )
        for item in items
        if isinstance(item, dict)
    ]


def _transform_quarters(payload: list[dict] | None) -> list[QuarterSummary]:
    return [
        QuarterSummary(
            quarter_id=parse_int(item.get("qusrterId")),
            quarter_name=clean_text(item.get("quarterName")),
            qtr_index=parse_int(item.get("qtrIndex")),
            start_date=normalize_date(item.get("startDate")),
            end_date=normalize_date(item.get("endDate")),
            extended_date=normalize_date(item.get("extendedDate")),
            payment_status=normalize_payment_status(item.get("paymentStatus")),
            status=clean_text(item.get("status")),
            submitted_on=normalize_datetime(item.get("submittedOn")),
        )
        for item in ensure_list(payload)
    ]


def _transform_progress_trend(payload: list[dict] | None) -> list[QuarterlyTrendPoint]:
    return [
        QuarterlyTrendPoint(
            quarter_name=clean_text(item.get("qtr_name")),
            progress_pct=parse_float(item.get("project_progress")),
        )
        for item in ensure_list(payload)
    ]


def _unwrap_result_list(payload: Any) -> list[dict]:
    if isinstance(payload, dict):
        result = payload.get("result")
        if isinstance(result, list):
            return result
    return []


def _transform_documents(
    doc_payload: dict | None,
    registration: Registration,
    promoter: Promoter,
    listing_entry: dict | None,
    base_url: str,
) -> dict[str, Any]:
    if not isinstance(doc_payload, dict):
        return {
            "certificate": {
                "uid": registration.certificate_uid,
                "download_url": registration.certificate_download_url,
            }
        }

    def group_docs(prefix: str, values: dict) -> list[dict[str, str]]:
        docs: list[dict[str, str]] = []
        for key, value in values.items():
            if key.lower().endswith("uid") and value:
                docs.append(
                    {
                        "label": f"{prefix}:{key}",
                        "uid": value,
                        "download_url": download_url(base_url, value),
                    }
                )
        return docs

    projectdoc = doc_payload.get("projectdoc") or {}
    findoc = doc_payload.get("findoc") or {}
    return {
        "certificate": {
            "uid": registration.certificate_uid,
            "download_url": registration.certificate_download_url,
        },
        "project_image": {
            "uid": listing_entry.get("projectImageUId") if listing_entry else None,
            "download_url": download_url(base_url, listing_entry.get("projectImageUId"))
            if listing_entry
            else None,
        },
        "project_brochure": {
            "uid": listing_entry.get("projectBroucherUId") if listing_entry else None,
            "download_url": download_url(
                base_url, listing_entry.get("projectBroucherUId")
            )
            if listing_entry
            else None,
        },
        "promoter_registration_certificate": {
            "uid": promoter.registration_certificate_uid,
            "download_url": promoter.registration_certificate_download_url,
        },
        "project_docs": group_docs("projectdoc", projectdoc),
        "financial_docs": group_docs("findoc", findoc),
    }


async def get_project_detail(
    client: GujReraClient,
    project_reg_id: int,
    listing_entry: dict | None = None,
) -> ProjectDetail:
    tier_one = await asyncio.gather(
        fetch_all_data(client, project_reg_id),
        fetch_prev_project_list(client, project_reg_id),
        fetch_qpr_details(client, project_reg_id),
        fetch_progress_report(client, project_reg_id),
        fetch_project_people(client, project_reg_id),
        fetch_documents(client, project_reg_id),
        fetch_applications(client, project_reg_id),
        fetch_block_list(client, project_reg_id),
        fetch_block_chart(client, project_reg_id),
        fetch_unit_details(client, project_reg_id),
        fetch_quarters(client, project_reg_id),
        fetch_progress_trend(client, project_reg_id),
        fetch_qtr_form_ids(client, project_reg_id),
        fetch_geo(client, project_reg_id),
        fetch_form5(client, project_reg_id),
        return_exceptions=True,
    )
    (
        d1_raw,
        d2_raw,
        d3_raw,
        d4_raw,
        d5_raw,
        d6_raw,
        d7_raw,
        d11_raw,
        d12_raw,
        d13_raw,
        d14_raw,
        d15_raw,
        d16_raw,
        d19_raw,
        d20_raw,
    ) = tier_one

    d1 = _safe_payload(d1_raw)
    if not isinstance(d1, dict) or not d1:
        raise ProjectNotFoundError(project_reg_id)

    d2 = _safe_payload(d2_raw)
    d3 = _safe_payload(d3_raw)
    d4 = _safe_payload(d4_raw)
    d5 = _safe_payload(d5_raw)
    d6 = _safe_payload(d6_raw)
    d7 = _safe_payload(d7_raw)
    d11 = _safe_payload(d11_raw)
    d12 = _safe_payload(d12_raw)
    d13 = _safe_payload(d13_raw)
    d14 = _safe_payload(d14_raw)
    d15 = _safe_payload(d15_raw)
    d16 = _safe_payload(d16_raw)
    d19 = _safe_payload(d19_raw)
    d20 = _safe_payload(d20_raw)

    promoter_id = parse_int(d1.get("promoterId"))
    form_one_id = parse_int(d16.get("formOneId")) if isinstance(d16, dict) else None
    form_three_id = (
        parse_int(d16.get("formThreeId")) if isinstance(d16, dict) else None
    )
    block_names = [
        clean_text(item.get("blockName"))
        for item in ensure_list(d11)
        if isinstance(item, dict)
    ]

    tier_two = await asyncio.gather(
        fetch_promoter(client, promoter_id, project_reg_id) if promoter_id else asyncio.sleep(0, result=None),
        fetch_collection_account(client, project_reg_id),
        fetch_retention_account(client, project_reg_id),
        fetch_construction_timeline(client, form_one_id, project_reg_id)
        if form_one_id
        else asyncio.sleep(0, result=None),
        fetch_inventory(client, form_three_id, block_names, project_reg_id)
        if form_three_id and block_names
        else asyncio.sleep(0, result=None),
        fetch_block_progress(client, form_one_id, project_reg_id)
        if form_one_id
        else asyncio.sleep(0, result=None),
        return_exceptions=True,
    )
    d10 = _safe_payload(tier_two[0])
    d8 = _safe_payload(tier_two[1])
    d9 = _safe_payload(tier_two[2])
    d17 = _safe_payload(tier_two[3])
    d18 = _safe_payload(tier_two[4])
    d21 = _safe_payload(tier_two[5])

    listing_entry = listing_entry or {}
    primary_project = _first_matching_project(d2, project_reg_id)
    registration = Registration(
        project_reg_id=project_reg_id,
        project_reg_no=clean_text(
            coalesce(
                primary_project.get("registrationNo"),
                d1.get("projRegNo"),
                listing_entry.get("regNo"),
            )
        ),
        project_ack_no=clean_text(
            coalesce(d1.get("projectAckNo"), listing_entry.get("project_ack_no"))
        ),
        project_name=clean_text(
            coalesce(
                primary_project.get("projectName"),
                d1.get("projectName"),
                listing_entry.get("projectName"),
            )
        ),
        project_type=clean_text(
            coalesce(primary_project.get("projectType"), d1.get("projectType"))
        ),
        project_status=clean_text(
            coalesce(primary_project.get("projectStatus"), listing_entry.get("project_status"))
        ),
        start_date=normalize_date(
            coalesce(primary_project.get("projectStartDate"), listing_entry.get("startDate"))
        ),
        original_end_date=normalize_date(
            coalesce(primary_project.get("projectEndDate"), listing_entry.get("endDate"))
        ),
        extended_end_date=normalize_date(listing_entry.get("extDate")),
        approved_on=normalize_date(
            coalesce(d1.get("approvedDate"), listing_entry.get("approvedOn"))
        ),
        has_extension=bool(listing_entry.get("extDate")),
        certificate_uid=clean_text(d1.get("certificateUid")),
        certificate_download_url=download_url(
            client.settings.gujrera_base_url, clean_text(d1.get("certificateUid"))
        ),
        wfo_id=clean_text(coalesce(d1.get("wfoId"), listing_entry.get("wfoid"))),
        last_updated_on=normalize_datetime(primary_project.get("lastUpdatedOn")),
    )

    promoter = Promoter(
        promoter_id=promoter_id,
        name=clean_text(coalesce(d10.get("promoterName") if isinstance(d10, dict) else None, d1.get("promoterName"), listing_entry.get("promoterName"))),
        type=clean_text(coalesce(d10.get("promoterType") if isinstance(d10, dict) else None, d1.get("promoterType"))),
        email_id=clean_text(coalesce(d10.get("emailId") if isinstance(d10, dict) else None, d1.get("promoterEmailId"), listing_entry.get("pmtr_email_id"))),
        mobile_no=clean_text(coalesce(d10.get("mobileNo") if isinstance(d10, dict) else None, d1.get("promoterMobileNo"), listing_entry.get("pr_mobile_no"))),
        address=clean_text(
            coalesce(
                (f"{d10.get('address')}, {d10.get('address2')}" if isinstance(d10, dict) and d10.get("address2") else d10.get("address") if isinstance(d10, dict) else None),
                listing_entry.get("promoterAddress"),
            )
        ),
        taluka_name=clean_text(d10.get("talukaName") if isinstance(d10, dict) else None),
        pan_no_masked=clean_text(listing_entry.get("prmtr_pan_no")),
        company_reg_no=clean_text(
            coalesce(
                d10.get("companyRegistrationNumber") if isinstance(d10, dict) else None,
                listing_entry.get("prmtr_com_reg_no"),
            )
        ),
        registration_certificate_uid=clean_text(
            d10.get("registrationCertificateUId") if isinstance(d10, dict) else None
        ),
        registration_certificate_download_url=download_url(
            client.settings.gujrera_base_url,
            clean_text(
                d10.get("registrationCertificateUId") if isinstance(d10, dict) else None
            ),
        ),
    )

    unit_summary_row = ensure_list(d13)[0] if ensure_list(d13) else {}
    trend = _transform_progress_trend(d15)
    progress = Progress(
        score=parse_float(d4.get("score")) if isinstance(d4, dict) else None,
        label=clean_text(d4.get("progress")) if isinstance(d4, dict) else None,
        arch_score=parse_float(d4.get("archScore")) if isinstance(d4, dict) else None,
        engg_score=parse_float(d4.get("enggScore")) if isinstance(d4, dict) else None,
        time_laps_ratio=parse_float(d4.get("timeLaps")) if isinstance(d4, dict) else None,
        quarterly_trend=trend,
    )

    financials = Financials(
        total_project_cost=parse_float(
            coalesce(
                d3.get("totalProjectCost") if isinstance(d3, dict) else None,
                listing_entry.get("projectCost"),
                listing_entry.get("total_est_cost_of_proj"),
            )
        ),
        registration_fee=parse_float(listing_entry.get("regFee")),
        payment_status=normalize_payment_status(listing_entry.get("payment_status")),
        min_unit_cost=parse_float(unit_summary_row.get("mincost")),
        max_unit_cost=parse_float(unit_summary_row.get("maxcost")),
        total_units=parse_int(unit_summary_row.get("totunit")),
        inventory_by_block=[
            {
                "block_name": clean_text(item.get("block_name")),
                "count": parse_int(item.get("cnt")),
            }
            for item in ensure_list(d3.get("inventoryCountDetails") if isinstance(d3, dict) else None)
        ],
    )

    booking_by_name = {
        clean_text(item.get("bname")): item for item in ensure_list(d12)
    }
    progress_by_name = {
        clean_text(item.get("blk_name")): item for item in ensure_list(d21)
    }
    timeline_by_name = {
        clean_text(item.get("blockName")): item
        for item in ensure_list(d17.get("formOneAList") if isinstance(d17, dict) else None)
    }
    blocks: list[BlockDetail] = []
    construction_timeline: list[dict[str, Any]] = []
    for item in ensure_list(d11):
        block_name = clean_text(item.get("blockName"))
        booking = booking_by_name.get(block_name) or {}
        progress_item = progress_by_name.get(block_name) or {}
        timeline_item = timeline_by_name.get(block_name) or {}
        phases = _timeline_phases(timeline_item) if timeline_item else BlockConstructionPhases()
        blocks.append(
            BlockDetail(
                block_id=parse_int(item.get("blockId")),
                block_name=block_name,
                dev_start_date=normalize_date(item.get("devStartDate")),
                dev_end_date=normalize_date(item.get("devEndDate")),
                height_meters=parse_float(item.get("height")),
                fsi=parse_float(item.get("fsi")),
                commencement_cert_no=clean_text(item.get("commencementCertiNo")),
                commencement_certificate_uid=clean_text(item.get("commencementCertificateUId")),
                commencement_certificate_download_url=download_url(
                    client.settings.gujrera_base_url,
                    clean_text(item.get("commencementCertificateUId")),
                ),
                units_booked=parse_int(booking.get("booked")),
                units_unbooked=parse_int(booking.get("unbooked")),
                booking_pct=parse_float(booking.get("perc")),
                block_progress_pct=parse_float(
                    coalesce(progress_item.get("block_progress"), timeline_item.get("blockProgress"))
                ),
                construction_phases=phases,
            )
        )
        if timeline_item:
            construction_timeline.append(
                {
                    "block_id": parse_int(timeline_item.get("blockId")),
                    "block_name": block_name,
                    "block_progress_pct": parse_float(timeline_item.get("blockProgress")),
                    "phases": phases.model_dump(),
                }
            )

    units_summary = UnitsSummary(
        total_units=parse_int(unit_summary_row.get("totunit")),
        min_cost=parse_float(unit_summary_row.get("mincost")),
        max_cost=parse_float(unit_summary_row.get("maxcost")),
        total_carpet_area_sqm=parse_float(unit_summary_row.get("totcararea")),
        min_carpet_area_sqm=parse_float(unit_summary_row.get("mincararea")),
        max_carpet_area_sqm=parse_float(unit_summary_row.get("maxcararea")),
        average_unit_size_sqm=parse_float(unit_summary_row.get("averageunit")),
    )

    inventory_form_three_id, inventory = _transform_inventory(d18)
    quarters = _transform_quarters(d14)
    location = Location(
        address=clean_text(d19.get("address")) if isinstance(d19, dict) else None,
        district=clean_text(d19.get("districtName")) if isinstance(d19, dict) else None,
        taluka=clean_text(d19.get("subDistrictName")) if isinstance(d19, dict) else None,
        coordinates=map_coordinates(d19.get("coordinates") if isinstance(d19, dict) else None),
        process_type=clean_text(d19.get("processType")) if isinstance(d19, dict) else None,
    )

    applications = [
        ApplicationRecord(
            application_number=clean_text(item.get("application_number")),
            approval_date=normalize_datetime(item.get("approval_date")),
            type=clean_text(item.get("type")),
        )
        for item in ensure_list(d7)
    ]

    annual_audits = [
        AnnualAuditRecord(
            financial_year=clean_text(item.get("projectFinancialYear")),
            status=clean_text(item.get("projectFinancialYearStatus")),
            submitted_on=normalize_datetime(item.get("submittedOn")),
            pdf_uid=clean_text(item.get("pdfUid")),
            pdf_download_url=download_url(
                client.settings.gujrera_base_url, clean_text(item.get("pdfUid"))
            ),
        )
        for item in ensure_list(d20)
    ]

    documents = _transform_documents(
        d6,
        registration,
        promoter,
        primary_project,
        client.settings.gujrera_base_url,
    )
    professionals = {}
    if isinstance(d5, dict):
        professionals = {
            "engineers": ensure_list(
                d5.get("projectEngineerList")
                or d5.get("engineerList")
                or d5.get("structuralEngineerList")
            ),
            "developers": ensure_list(d5.get("projectDeveloperList") or d5.get("developerList")),
            "raw": d5,
        }

    return ProjectDetail(
        registration=registration,
        promoter=promoter,
        financials=financials,
        progress=progress,
        blocks=blocks,
        units_summary=units_summary,
        inventory=inventory,
        quarters=quarters,
        construction_timeline=construction_timeline,
        location=location,
        applications=applications,
        bank_accounts=BankAccounts(
            collection_account=_transform_bank_account(d8),
            retention_account=_transform_bank_account(d9),
        ),
        annual_audits=annual_audits,
        documents=documents,
        professionals=professionals,
    )


async def get_inventory_only(
    client: GujReraClient, project_reg_id: int
) -> InventoryResponse:
    project_payload = unwrap_data(
        await fetch_all_data(client, project_reg_id)
    )
    if not isinstance(project_payload, dict) or not project_payload:
        raise ProjectNotFoundError(project_reg_id)
    form_payload = unwrap_data(
        await fetch_qtr_form_ids(client, project_reg_id)
    )
    if not isinstance(form_payload, dict) or not form_payload.get("formThreeId"):
        return InventoryResponse(project_reg_id=project_reg_id, form_three_id=None, inventory=[])
    block_payload = unwrap_data(
        await fetch_block_list(client, project_reg_id)
    )
    block_names = [
        clean_text(item.get("blockName"))
        for item in ensure_list(block_payload)
        if isinstance(item, dict)
    ]
    inventory_payload = await fetch_inventory(
        client,
        int(form_payload["formThreeId"]),
        block_names,
        project_reg_id,
    )
    form_three_id, inventory = _transform_inventory(inventory_payload)
    return InventoryResponse(
        project_reg_id=project_reg_id,
        form_three_id=form_three_id,
        inventory=inventory,
    )


async def get_quarters_only(
    client: GujReraClient, project_reg_id: int
) -> QuartersResponse:
    project_payload = unwrap_data(
        await fetch_all_data(client, project_reg_id)
    )
    if not isinstance(project_payload, dict) or not project_payload:
        raise ProjectNotFoundError(project_reg_id)
    quarters_payload, trend_payload = await asyncio.gather(
        fetch_quarters(client, project_reg_id),
        fetch_progress_trend(client, project_reg_id),
    )
    return QuartersResponse(
        project_reg_id=project_reg_id,
        quarters=_transform_quarters(unwrap_data(quarters_payload)),
        quarterly_trend=_transform_progress_trend(unwrap_data(trend_payload)),
    )


async def get_quarter_detail(
    client: GujReraClient, project_reg_id: int, quarter_id: int
) -> QuarterDetail:
    project_payload = unwrap_data(
        await fetch_all_data(client, project_reg_id)
    )
    if not isinstance(project_payload, dict) or not project_payload:
        raise ProjectNotFoundError(project_reg_id)

    quarters_payload, trend_payload, public_forms_payload, enquiry_payload = await asyncio.gather(
        fetch_quarters(client, project_reg_id),
        fetch_progress_trend(client, project_reg_id),
        fetch_public_quarter_forms(client, project_reg_id),
        fetch_quarter_enquiry_status(client, project_reg_id),
    )
    quarters = _transform_quarters(unwrap_data(quarters_payload))
    trend = _transform_progress_trend(unwrap_data(trend_payload))
    selected = next((item for item in quarters if item.quarter_id == quarter_id), None)
    if selected is None:
        raise ProjectNotFoundError(f"{project_reg_id}/quarter/{quarter_id}")

    progress_pct = None
    delta_from_previous = None
    if selected.qtr_index and 0 < selected.qtr_index <= len(trend):
        current = trend[selected.qtr_index - 1]
        progress_pct = current.progress_pct
        if selected.qtr_index > 1:
            previous = trend[selected.qtr_index - 2].progress_pct
            if previous is not None and progress_pct is not None:
                delta_from_previous = progress_pct - previous

    public_form = next(
        (
            item
            for item in _unwrap_result_list(public_forms_payload)
            if clean_text(item.get("application_Type")) == selected.quarter_name
        ),
        None,
    )
    public_documents = {}
    if isinstance(public_form, dict):
        public_documents = {
            "application_type": clean_text(public_form.get("application_Type")),
            "submission_date": normalize_datetime(public_form.get("submission_Date")),
            "form_one_pdf": {
                "uid": clean_text(public_form.get("form_one_pdf_uid")),
                "download_url": download_url(
                    client.settings.gujrera_base_url,
                    clean_text(public_form.get("form_one_pdf_uid")),
                ),
            },
            "form_two_pdf": {
                "uid": clean_text(public_form.get("form_two_pdf_uid")),
                "download_url": download_url(
                    client.settings.gujrera_base_url,
                    clean_text(public_form.get("form_two_pdf_uid")),
                ),
            },
            "form_three_pdf": {
                "uid": clean_text(public_form.get("form_three_pdf_uid")),
                "download_url": download_url(
                    client.settings.gujrera_base_url,
                    clean_text(public_form.get("form_three_pdf_uid")),
                ),
            },
            "form_eight_pdf": {
                "uid": clean_text(public_form.get("form_eight_doc_uid")),
                "download_url": download_url(
                    client.settings.gujrera_base_url,
                    clean_text(public_form.get("form_eight_doc_uid")),
                ),
            },
        }

    enquiry_open = None
    enquiry_data = unwrap_data(enquiry_payload)
    if isinstance(enquiry_data, dict) and isinstance(enquiry_data.get("data"), bool):
        enquiry_open = enquiry_data.get("data")

    return QuarterDetail(
        project_reg_id=project_reg_id,
        quarter_id=quarter_id,
        quarter_name=selected.quarter_name,
        qtr_index=selected.qtr_index,
        start_date=selected.start_date,
        end_date=selected.end_date,
        extended_date=selected.extended_date,
        payment_status=selected.payment_status,
        status=selected.status,
        submitted_on=selected.submitted_on,
        progress_pct=progress_pct,
        delta_from_previous_pct=delta_from_previous,
        enquiry_open=enquiry_open,
        public_documents=public_documents,
    )
