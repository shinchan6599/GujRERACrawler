from __future__ import annotations

from collections import defaultdict

from app.db.store import LocalStore
from app.schemas.rag import RagAnswerResponse, RagSearchResponse, RagSearchResult


async def search_local_knowledge(
    store: LocalStore,
    *,
    query: str,
    limit: int,
    project_reg_id: int | None = None,
    section: str | None = None,
) -> RagSearchResponse:
    results = await store.search_chunks(
        query=query,
        limit=limit,
        project_reg_id=project_reg_id,
        section=section,
    )
    return RagSearchResponse(
        query=query,
        total_results=len(results),
        results=[RagSearchResult(**row) for row in results],
    )


async def answer_from_local_knowledge(
    store: LocalStore,
    *,
    query: str,
    limit: int,
    project_reg_id: int | None = None,
    section: str | None = None,
) -> RagAnswerResponse:
    search = await search_local_knowledge(
        store,
        query=query,
        limit=limit,
        project_reg_id=project_reg_id,
        section=section,
    )
    if not search.results:
        return RagAnswerResponse(
            query=query,
            answer="No matching local project records were found in the synced database.",
            total_results=0,
            citations=[],
        )

    grouped: dict[int, list[RagSearchResult]] = defaultdict(list)
    for result in search.results:
        grouped[result.project_reg_id].append(result)

    lines = [
        f"Found {len(search.results)} relevant local records across {len(grouped)} projects."
    ]
    for project_results in list(grouped.values())[:4]:
        head = project_results[0]
        lines.append(
            f"{head.project_name or 'Unknown project'} ({head.reg_no or 'no reg no'}, {head.district_name or 'unknown district'}):"
        )
        for result in project_results[:3]:
            lines.append(f"- [{result.section}] {result.snippet}")

    return RagAnswerResponse(
        query=query,
        answer="\n".join(lines),
        total_results=search.total_results,
        citations=search.results,
    )
