"""Shape database rows into graph node dicts compatible with /expand."""

from codegraph_core.graph.node_specs import get_node_spec


def shape_node(node_type: str, row: dict) -> dict:
    spec = get_node_spec(node_type)
    if spec is None:
        raise ValueError(f"Unknown node type: {node_type}")
    return {
        "type": node_type,
        "id": row[spec.id_column],
        "title": row.get(spec.title),
        "subtitle": row.get(spec.subtitle),
    }
