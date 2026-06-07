"""Parameterised SQL generation for forward graph expansion."""

from codegraph_core.graph.node_specs import get_node_spec
from codegraph_core.graph.types import EdgeRule


def build_expand_query(rule: EdgeRule, node: dict, limit: int) -> tuple[str, tuple]:
    to_spec = get_node_spec(rule.to_type)
    if to_spec is None:
        raise ValueError(f"Unknown to_type: {rule.to_type}")
    if not isinstance(limit, int) or limit < 0:
        raise ValueError("limit must be a non-negative int")

    cols = f"`{to_spec.id_column}`, `{to_spec.title}`, `{to_spec.subtitle}`"
    table = f"`{to_spec.table}`"

    if rule.guard is not None:
        src_col, dst_col = rule.match[0]
        raw = node.get(src_col, "") or ""
        values = [v.strip() for v in str(raw).split(",") if v.strip()]
        if not values:
            sql = f"SELECT {cols} FROM {table} WHERE 1=0 LIMIT %s"
            return sql, (limit,)
        placeholders = ", ".join(["%s"] * len(values))
        sql = (
            f"SELECT {cols} FROM {table} WHERE `{dst_col}` IN ({placeholders}) LIMIT %s"
        )
        return sql, (*values, limit)

    clauses: list[str] = []
    params: list = []
    for src_col, dst_col in rule.match:
        clauses.append(f"`{dst_col}` = %s")
        params.append(node[src_col])
    where = " AND ".join(clauses)
    sql = f"SELECT {cols} FROM {table} WHERE {where} LIMIT %s"
    return sql, (*params, limit)
