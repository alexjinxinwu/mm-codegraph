"""Pydantic models for POST /expand."""

from pydantic import BaseModel, ConfigDict, Field


class NodeRef(BaseModel):
    type: str
    id: int = Field(gt=0)


class ExpandRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schema_: str = Field(alias="schema")
    node: NodeRef
    edgeIds: list[str] | None = None


class GraphNode(BaseModel):
    type: str
    id: int
    title: str | None = None
    subtitle: str | None = None


class GraphEdge(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ruleId: str
    from_: NodeRef = Field(alias="from")
    to: NodeRef
    label: str


class ExpandResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
