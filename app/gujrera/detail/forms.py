import asyncio

from app.client import GujReraClient


async def fetch_construction_timeline(
    client: GujReraClient, form_one_id: int, project_reg_id: int
):
    return await client.get_json(
        f"/formone/public/getfrom-one-byformone-id/{form_one_id}",
        endpoint_name="D17_construction_timeline",
        project_reg_id=project_reg_id,
    )


async def fetch_inventory(
    client: GujReraClient,
    form_three_id: int,
    block_names: list[str],
    project_reg_id: int,
):
    unique_block_names = [name for name in dict.fromkeys(block_names) if name]
    if not unique_block_names:
        return {"formThreeId": form_three_id, "formThreeAList": []}

    headers = {
        "Content-Type": "application/json",
        "Origin": client.settings.gujrera_base_url,
        "Referer": f"{client.settings.gujrera_base_url.rstrip('/')}/",
    }
    results = await asyncio.gather(
        *[
            client.post_json(
                "/formthree/public/get-inv-details-for-view",
                json_body={"blockName": block_name, "formThreeId": form_three_id},
                endpoint_name="D18_inventory_by_block",
                project_reg_id=project_reg_id,
                headers=headers,
            )
            for block_name in unique_block_names
        ],
        return_exceptions=True,
    )

    merged_rows: list[dict] = []
    seen_keys: set[tuple] = set()
    for block_name, result in zip(unique_block_names, results):
        if isinstance(result, Exception) or result is None:
            continue
        if isinstance(result, dict):
            rows = result.get("data", result)
        else:
            rows = result
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            row.setdefault("blockName", block_name)
            dedupe_key = (
                row.get("blockName"),
                row.get("flatNo"),
                row.get("usage"),
                row.get("alloteeName"),
                row.get("unitConsideration"),
            )
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            merged_rows.append(row)

    return {"formThreeId": form_three_id, "formThreeAList": merged_rows}
