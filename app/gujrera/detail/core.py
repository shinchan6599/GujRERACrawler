from app.client import GujReraClient


async def fetch_all_data(client: GujReraClient, project_reg_id: int):
    return await client.get_json(
        f"/project_reg/public/alldatabyprojectid/{project_reg_id}",
        endpoint_name="D1_all_data",
        project_reg_id=project_reg_id,
    )


async def fetch_prev_project_list(client: GujReraClient, project_reg_id: int):
    return await client.get_json(
        f"/project_reg/public/getprev-project-list/{project_reg_id}",
        endpoint_name="D2_prev_project_list",
        project_reg_id=project_reg_id,
    )


async def fetch_project_people(client: GujReraClient, project_reg_id: int):
    return await client.get_json(
        f"/project_reg/public/getproject-details/{project_reg_id}",
        endpoint_name="D5_project_people",
        project_reg_id=project_reg_id,
    )


async def fetch_documents(client: GujReraClient, project_reg_id: int):
    return await client.get_json(
        f"/project_reg/public/getproject-doc/{project_reg_id}",
        endpoint_name="D6_documents",
        project_reg_id=project_reg_id,
    )


async def fetch_applications(client: GujReraClient, project_reg_id: int):
    return await client.get_json(
        f"/project_reg/public/projectAllApplications/{project_reg_id}",
        endpoint_name="D7_applications",
        project_reg_id=project_reg_id,
    )


async def fetch_collection_account(client: GujReraClient, project_reg_id: int):
    return await client.get_json(
        f"/project_reg/public/bank/get_col_account/{project_reg_id}",
        endpoint_name="D8_collection_account",
        project_reg_id=project_reg_id,
    )


async def fetch_retention_account(client: GujReraClient, project_reg_id: int):
    return await client.get_json(
        f"/project_reg/public/project-app/getproject-banks/{project_reg_id}",
        endpoint_name="D9_retention_account",
        project_reg_id=project_reg_id,
    )


async def fetch_promoter(client: GujReraClient, promoter_id: int, project_reg_id: int):
    return await client.get_json(
        f"/user_reg/promoter/promoter{promoter_id}",
        endpoint_name="D10_promoter",
        project_reg_id=project_reg_id,
    )
