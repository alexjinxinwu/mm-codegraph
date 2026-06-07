"""codegraph-core — shared query engine, data models, and utilities.

Both codegraph-mcp (stdio transport) and codegraph-server (HTTP transport)
import from this package. All query primitives, connection pool management,
and schema validation live here — ensuring zero behavioral difference
across transports.
"""

from .graph import (
    EDGE_RULES,
    NODE_SPECS,
    build_expand_query,
    get_edge_rule,
    get_edges_from,
    get_node_spec,
)
from .query_engine import QueryEngine
from .pool_manager import PoolManager
from .schema_validator import SchemaValidator

__all__ = [
    "QueryEngine",
    "PoolManager",
    "SchemaValidator",
    "NODE_SPECS",
    "EDGE_RULES",
    "build_expand_query",
    "get_node_spec",
    "get_edges_from",
    "get_edge_rule",
]