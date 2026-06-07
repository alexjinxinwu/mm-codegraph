"""SchemaValidator — centralized schema validation before query execution."""

import re
from typing import List


SCHEMA_RE = re.compile(r"^[A-Za-z0-9_.]+$")
SYSTEM_SCHEMAS = {"information_schema", "mysql", "performance_schema", "sys"}


class SchemaValidator:
    """Centralized schema validation.

    All schema checks happen here before query execution.
    This guarantees identical validation rules for MCP and HTTP transports.
    """

    @classmethod
    def validate(cls, schema: str) -> str:
        """Validate schema name.

        Returns the validated schema string.
        Raises ValueError if schema name is invalid.
        """
        if not schema or not SCHEMA_RE.match(schema):
            raise ValueError(f"非法 schema 名: {schema!r}（只允许字母、数字、下划线、点）")
        return schema

    @classmethod
    def is_system_schema(cls, schema: str) -> bool:
        """Return True if schema is a MySQL system schema (should be excluded from listings)."""
        return schema.lower() in SYSTEM_SCHEMAS

    @classmethod
    def filter_non_system_schemas(cls, schemas: List[str]) -> List[str]:
        """Filter out MySQL system schemas from a list."""
        return [s for s in schemas if not cls.is_system_schema(s)]