from fastapi import APIRouter, Depends, Query, Request

from app.config import Settings, get_settings
from app.db.store import LocalStore
from app.rag.service import answer_from_local_knowledge, search_local_knowledge
from app.schemas.rag import RagAnswerRequest, RagAnswerResponse, RagSearchResponse

router = APIRouter(prefix="/api/rag", tags=["rag"])


def get_store(request: Request) -> LocalStore:
    return request.app.state.local_store


@router.get("/search", response_model=RagSearchResponse)
async def rag_search(
    q: str = Query(..., min_length=2),
    limit: int | None = Query(default=None, ge=1, le=50),
    project_reg_id: int | None = Query(default=None),
    section: str | None = Query(default=None),
    store: LocalStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
) -> RagSearchResponse:
    return await search_local_knowledge(
        store,
        query=q,
        limit=limit or settings.rag_default_limit,
        project_reg_id=project_reg_id,
        section=section,
    )


@router.post("/answer", response_model=RagAnswerResponse)
async def rag_answer(
    payload: RagAnswerRequest,
    store: LocalStore = Depends(get_store),
) -> RagAnswerResponse:
    return await answer_from_local_knowledge(
        store,
        query=payload.query,
        limit=payload.limit,
        project_reg_id=payload.project_reg_id,
        section=payload.section,
    )
