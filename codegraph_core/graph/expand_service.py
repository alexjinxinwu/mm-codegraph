"""Orchestrate forward graph expansion: hydrate → build_expand_query → shape."""

from dataclasses import dataclass

from codegraph_core.graph.edge_rules import get_edges_from
from codegraph_core.graph.expand_query import build_expand_query
from codegraph_core.graph.expand_validation import validate_expand_input
from codegraph_core.graph.node_specs import get_node_spec
from codegraph_core.query_engine import q

EXPAND_NEIGHBOR_LIMIT = 200


@dataclass
class ExpandResult:
    nodes: list[dict]
    edges: list[dict]


def _source_columns_for_type(node_type: str) -> set[str]:
    cols: set[str] = set()
    for rule in get_edges_from(node_type):
        for src, _ in rule.match:
            cols.add(src)
    return cols


def hydrate_node(
    schema: str,
    node_type: str,
    node_id: int,
    q_fn=q,
) -> dict | None:
    spec = get_node_spec(node_type)
    if spec is None:
        raise ValueError(f"Unknown node type: {node_type}")
    src_cols = _source_columns_for_type(node_type)
    select_cols = sorted({spec.id_column, spec.title, spec.subtitle} | src_cols)
    quoted = ", ".join(f"`{c}`" for c in select_cols)
    sql = (
        f"SELECT {quoted} FROM `{spec.table}` "
        f"WHERE `{spec.id_column}` = %s LIMIT 1"
    )
    rows = q_fn(schema, sql, (node_id,))
    return rows[0] if rows else None


def _shape_neighbor(
    rule,
    from_type: str,
    from_id: int,
    neighbor_row: dict,
) -> tuple[dict, dict]:
    to_spec = get_node_spec(rule.to_type)
    assert to_spec is not None
    node = {
        "type": rule.to_type,
        "id": neighbor_row[to_spec.id_column],
        "title": neighbor_row.get(to_spec.title),
        "subtitle": neighbor_row.get(to_spec.subtitle),
    }
    edge = {
        "ruleId": rule.id,
        "from": {"type": from_type, "id": from_id},
        "to": {"type": rule.to_type, "id": neighbor_row[to_spec.id_column]},
        "label": rule.label,
    }
    return node, edge


def expand_neighbors(
    schema: str,
    node_type: str,
    node_id: int,
    edge_ids: list[str] | None = None,
    limit: int = EXPAND_NEIGHBOR_LIMIT,
    q_fn=q,
) -> ExpandResult:
    validate_expand_input(schema, node_type, node_id, edge_ids)
    row = hydrate_node(schema, node_type, node_id, q_fn=q_fn)
    if row is None:
        return ExpandResult(nodes=[], edges=[])

    from_spec = get_node_spec(node_type)
    assert from_spec is not None
    from_id = row[from_spec.id_column]

    rules = get_edges_from(node_type)
    if edge_ids:
        allowed = set(edge_ids)
        rules = [r for r in rules if r.id in allowed]

    nodes_by_key: dict[tuple[str, int], dict] = {}
    edges_by_key: dict[tuple, dict] = {}

    for rule in rules:
        sql, params = build_expand_query(rule, row, limit)
        neighbors = q_fn(schema, sql, params)
        for neighbor_row in neighbors:
            node, edge = _shape_neighbor(rule, node_type, from_id, neighbor_row)
            nodes_by_key[(node["type"], node["id"])] = node
            edge_key = (
                edge["ruleId"],
                edge["from"]["type"],
                edge["from"]["id"],
                edge["to"]["type"],
                edge["to"]["id"],
            )
            edges_by_key[edge_key] = edge

    return ExpandResult(
        nodes=list(nodes_by_key.values()),
        edges=list(edges_by_key.values()),
    )
