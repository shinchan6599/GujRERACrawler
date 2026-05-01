from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RagSearchResult(BaseModel):
    chunk_id: int
    project_reg_id: int
    project_name: str | None = None
    reg_no: str | None = None
    district_name: str | None = None
    section: str
    title: str
    content: str
    snippet: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagSearchResponse(BaseModel):
    query: str
    total_results: int
    results: list[RagSearchResult] = Field(default_factory=list)


class RagAnswerRequest(BaseModel):
    query: str
    limit: int = 8
    project_reg_id: int | None = None
    section: str | None = None


class RagAnswerResponse(BaseModel):
    query: str
    answer: str
    total_results: int
    citations: list[RagSearchResult] = Field(default_factory=list)
