"""Input validation for entry resolve — no database access."""

from codegraph_core.graph.entry_resolvers import get_resolver
from codegraph_core.schema_validator import SchemaValidator


def validate_resolve_input(schema: str, kind: str, value: str) -> None:
    SchemaValidator.validate(schema)
    if not value or not str(value).strip():
        raise ValueError("value must be non-empty")
    if get_resolver(kind) is None:
        raise ValueError(f"Unknown resolver kind: {kind}")
