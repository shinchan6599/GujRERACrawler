from app.client import GujReraClient


async def fetch_qpr_details(client: GujReraClient, project_reg_id: int):
    return await client.get_json(
        f"/project_reg/public/project-app/get-project-details-for-qpr/{project_reg_id}",
        endpoint_name="D3_qpr_details",
        project_reg_id=project_reg_id,
    )


async def fetch_progress_report(client: GujReraClient, project_reg_id: int):
    return await client.get_json(
        f"/project_reg/public/getProjectProgressReports-ByPrjRegId/{project_reg_id}",
        endpoint_name="D4_progress_report",
        project_reg_id=project_reg_id,
    )


async def fetch_block_list(client: GujReraClient, project_reg_id: int):
    return await client.get_json(
        f"/project_reg/project-app/getproject-blocklist/{project_reg_id}",
        endpoint_name="D11_block_list",
        project_reg_id=project_reg_id,
    )


async def fetch_block_chart(client: GujReraClient, project_reg_id: int):
    return await client.get_json(
        f"/dashboard/get-all-block-chart-details-by-id/{project_reg_id}",
        endpoint_name="D12_block_chart",
        project_reg_id=project_reg_id,
    )


async def fetch_unit_details(client: GujReraClient, project_reg_id: int):
    return await client.get_json(
        f"/dashboard/get-all-view-unit-details-by-id/{project_reg_id}",
        endpoint_name="D13_unit_details",
        project_reg_id=project_reg_id,
    )
