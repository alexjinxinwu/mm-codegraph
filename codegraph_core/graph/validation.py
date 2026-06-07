"""Registry validation — run at import time."""

from codegraph_core.graph.edge_rules import EDGE_RULES, _validate_edge_rules
from codegraph_core.graph.entry_resolvers import _validate_entry_resolvers
from codegraph_core.graph.node_specs import NODE_SPECS, _validate_node_specs


def validate_registries() -> None:
    _validate_node_specs()
    _validate_edge_rules(NODE_SPECS)
    _validate_entry_resolvers(NODE_SPECS)
