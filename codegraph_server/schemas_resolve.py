"""Pydantic models for GET /resolve."""

from pydantic import BaseModel


class GraphNodeOut(BaseModel):
    type: str
    id: int
    title: str | None = None
    subtitle: str | None = None


class ResolveResponse(BaseModel):
    status: str
    roots: list[GraphNodeOut]
    candidates: list[GraphNodeOut]
