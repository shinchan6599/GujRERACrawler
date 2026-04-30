from app.client import GujReraClient


async def fetch_geo(client: GujReraClient, project_reg_id: int):
    return await client.get_json(
        f"/maplocation/public/getProjectLocations/{project_reg_id}",
        endpoint_name="D19_geo",
        project_reg_id=project_reg_id,
    )


async def fetch_form5(client: GujReraClient, project_reg_id: int):
    return await client.get_json(
        f"/form_five/get-formfive-records-till-date/{project_reg_id}",
        endpoint_name="D20_form5",
        project_reg_id=project_reg_id,
    )


async def fetch_block_progress(client: GujReraClient, form_one_id: int, project_reg_id: int):
    return await client.get_json(
        f"/dashboard//project-block-progress-dtl-by-prj-id/{form_one_id}",
        endpoint_name="D21_block_progress",
        project_reg_id=project_reg_id,
    )
