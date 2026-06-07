"""Input validation for graph expand — no database access."""

from codegraph_core.graph.edge_rules import get_edge_rule
from codegraph_core.graph.node_specs import get_node_spec
from codegraph_core.schema_validator import SchemaValidator


def validate_expand_input(
    schema: str,
    node_type: str,
    node_id: int,
    edge_ids: list[str] | None,
) -> None:
    SchemaValidator.validate(schema)
    if node_id <= 0:
        raise ValueError("node.id must be a positive integer")
    if get_node_spec(node_type) is None:
        raise ValueError(f"Unknown node type: {node_type}")
    if not edge_ids:
        return
    for rule_id in edge_ids:
        rule = get_edge_rule(rule_id)
        if rule is None:
            raise ValueError(f"Unknown edge rule: {rule_id}")
        if rule.from_type != node_type:
            raise ValueError(f"Edge {rule_id} not applicable to {node_type}")
