"""Graph model kernel — NodeSpec, EDGE_RULES, and expand SQL generation."""

from codegraph_core.graph.edge_rules import EDGE_RULES, get_edge_rule, get_edges_from
from codegraph_core.graph.expand_query import build_expand_query
from codegraph_core.graph.expand_service import expand_neighbors
from codegraph_core.graph.node_specs import NODE_SPECS, get_node_spec
from codegraph_core.graph.validation import validate_registries

validate_registries()

__all__ = [
    "NODE_SPECS",
    "EDGE_RULES",
    "build_expand_query",
    "expand_neighbors",
    "get_edge_rule",
    "get_edges_from",
    "get_node_spec",
]
