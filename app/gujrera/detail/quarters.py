from app.client import GujReraClient


async def fetch_quarters(client: GujReraClient, project_reg_id: int):
    return await client.get_json(
        f"/quarter/public/getprojectqtrs/{project_reg_id}",
        endpoint_name="D14_quarters",
        project_reg_id=project_reg_id,
    )


async def fetch_progress_trend(client: GujReraClient, project_reg_id: int):
    return await client.get_json(
        f"/quarter/get-project-progress/{project_reg_id}",
        endpoint_name="D15_progress_trend",
        project_reg_id=project_reg_id,
    )


async def fetch_qtr_form_ids(client: GujReraClient, project_reg_id: int):
    return await client.get_json(
        f"/quarter/public/get-qtr-form-details/{project_reg_id}",
        endpoint_name="D16_qtr_form_ids",
        project_reg_id=project_reg_id,
    )


async def fetch_public_quarter_forms(client: GujReraClient, project_reg_id: int):
    return await client.get_json(
        f"/formone/public/getpublicform-one-form-two-id/{project_reg_id}",
        endpoint_name="Q2_public_quarter_forms",
        project_reg_id=project_reg_id,
    )


async def fetch_quarter_enquiry_status(client: GujReraClient, project_reg_id: int):
    return await client.get_json(
        f"/quarter/getQEEnquiryStatus/{project_reg_id}",
        endpoint_name="Q8_quarter_enquiry_status",
        project_reg_id=project_reg_id,
    )
