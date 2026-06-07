"""Resolve external identifiers to graph root nodes."""

from dataclasses import dataclass

from codegraph_core.graph.entry_resolvers import get_resolver
from codegraph_core.graph.node_specs import get_node_spec
from codegraph_core.graph.resolve_validation import validate_resolve_input
from codegraph_core.graph.shape import shape_node
from codegraph_core.graph.types import EntryResolver
from codegraph_core.query_engine import q

RESOLVE_MATCH_LIMIT = 50


@dataclass
class ResolveResult:
    status: str
    roots: list[dict]
    candidates: list[dict]


def build_resolve_query(resolver: EntryResolver, limit: int) -> str:
    spec = get_node_spec(resolver.node_type)
    if spec is None:
        raise ValueError(f"Unknown node type: {resolver.node_type}")
    return (
        f"SELECT `{spec.id_column}`, `{spec.title}`, `{spec.subtitle}` "
        f"FROM `{spec.table}` WHERE `{resolver.match_column}` = %s LIMIT %s"
    )


def resolve_entry(
    schema: str,
    kind: str,
    value: str,
    limit: int = RESOLVE_MATCH_LIMIT,
    q_fn=q,
) -> ResolveResult:
    validate_resolve_input(schema, kind, value)
    resolver = get_resolver(kind)
    assert resolver is not None

    sql = build_resolve_query(resolver, limit)
    rows = q_fn(schema, sql, (value.strip(), limit))

    if not rows:
        return ResolveResult(status="notFound", roots=[], candidates=[])

    nodes = [shape_node(resolver.node_type, row) for row in rows]
    if len(nodes) == 1:
        return ResolveResult(status="found", roots=nodes, candidates=[])
    return ResolveResult(status="multiple", roots=[], candidates=nodes)
