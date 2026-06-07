"""Graph metadata types — NodeSpec and EdgeRule."""

from dataclasses import dataclass


class RegistryError(Exception):
    """Raised when NODE_SPECS or EDGE_RULES fail validation."""


@dataclass(frozen=True)
class NodeSpec:
    node_type: str
    table: str
    id_column: str
    title: str
    subtitle: str


@dataclass(frozen=True)
class EdgeRule:
    id: str
    from_type: str
    to_type: str
    label: str
    match: tuple[tuple[str, str], ...]
    direction: str = "out"
    guard: str | None = None
    assumption: str | None = None


@dataclass(frozen=True)
class EntryResolver:
    kind: str
    node_type: str
    match_column: str
