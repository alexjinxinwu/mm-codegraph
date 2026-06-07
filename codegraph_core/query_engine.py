"""Query engine — query primitives (get_pool, q, _schema, out) in codegraph-core.

These primitives are the shared kernel used by both MCP stdio transport
and future HTTP transport. Behavior is identical regardless of caller.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import pymysql
from dbutils.pooled_db import PooledDB


SCHEMA_RE = re.compile(r"^[A-Za-z0-9_.]+$")
DEFAULT_LIMIT = 200
ALL_TABLES = [
    "activities", "beans", "bridges", "flow_tasks", "flows", "interceptors",
    "java_classes", "java_methods", "logic_steps", "logics",
    "module_parameters", "service_entries", "states", "transitions",
]

# Forbidden SQL keywords for sql_query safety check
_FORBIDDEN_RE = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|replace|grant|revoke|call|load|rename|into|outfile)\b",
    re.I,
)


class QueryEngine:
    """Shared query engine — single source of truth for all graph traversal.

    Both MCP server and HTTP server call QueryEngine methods.
    This guarantees zero behavioral difference across transports.
    """

    def __init__(self):
        self._pool: Optional[PooledDB] = None

    # ── Pool management ──────────────────────────────────────────────

    def get_pool(self) -> PooledDB:
        """Return the shared MySQL connection pool, creating it lazily."""
        if self._pool is None:
            self._pool = PooledDB(
                creator=pymysql,
                maxconnections=int(os.environ.get("MMCG_MYSQL_POOL_SIZE", "5")),
                host=os.environ.get("MMCG_MYSQL_HOST", "localhost"),
                port=int(os.environ.get("MMCG_MYSQL_PORT", "3306")),
                user=os.environ.get("MMCG_MYSQL_USER", "root"),
                password=os.environ.get("MMCG_MYSQL_PASSWORD", "root"),
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                ping=1,
            )
        return self._pool

    # ── Schema validation ───────────────────────────────────────────

    def _schema(self, schema: str) -> str:
        """Validate and return schema name. Raises ValueError if invalid."""
        if not schema or not SCHEMA_RE.match(schema):
            raise ValueError(f"非法 schema 名: {schema!r}（只允许字母、数字、下划线、点）")
        return schema

    # ── Query execution ─────────────────────────────────────────────

    def q(self, schema: str, sql: str, params: Tuple = ()) -> List[Dict]:
        """Execute a read-only query against the specified schema.

        Returns a list of row dictionaries.
        """
        schema = self._schema(schema)
        conn = self.get_pool().connection()
        try:
            with conn.cursor() as cur:
                cur.execute(f"USE `{schema}`")
                cur.execute(sql, params)
                return cur.fetchall()
        finally:
            conn.close()

    # ── Output formatting ───────────────────────────────────────────

    def out(self, data: Any) -> str:
        """Serialize data to JSON string with consistent formatting."""
        return json.dumps(data, ensure_ascii=False, indent=2, default=str)

    # ── Safety-checked raw SQL (for sql_query tool) ─────────────────

    def sql_query(self, schema: str, sql: str, limit: int = 200) -> List[Dict]:
        """Execute a raw read-only SQL query with safety checks.

        Only SELECT/WITH allowed. Forbidden keywords are blocked.
        A LIMIT is appended if not present.
        """
        s = sql.strip().rstrip(";").strip()
        if ";" in s:
            raise ValueError("只允许单条语句")
        if not re.match(r"^\s*(select|with)\b", s, re.I):
            raise ValueError("只允许 SELECT/WITH 查询")
        if _FORBIDDEN_RE.search(s):
            raise ValueError("检测到非只读关键字")
        if not re.search(r"\blimit\b", s, re.I):
            s = f"{s} LIMIT {int(limit)}"
        return self.q(schema, s)


# ── Module-level convenience functions ────────────────────────────────
# These delegate to a shared global engine instance so that existing
# code (including analyzer_compat.py via _mysql_q injection) can
# continue using the module-level API.

_GLOBAL_ENGINE: Optional[QueryEngine] = None


def _get_engine() -> QueryEngine:
    global _GLOBAL_ENGINE
    if _GLOBAL_ENGINE is None:
        _GLOBAL_ENGINE = QueryEngine()
    return _GLOBAL_ENGINE


def get_pool():
    """Module-level alias for QueryEngine.get_pool()."""
    return _get_engine().get_pool()


def q(schema: str, sql: str, params: Tuple = ()) -> List[Dict]:
    """Module-level alias for QueryEngine.q()."""
    return _get_engine().q(schema, sql, params)


def _schema(s: str) -> str:
    """Module-level alias for QueryEngine._schema()."""
    return _get_engine()._schema(s)


def out(data: Any) -> str:
    """Module-level alias for QueryEngine.out()."""
    return _get_engine().out(data)


def sql_query(schema: str, sql: str, limit: int = 200) -> List[Dict]:
    """Module-level alias for QueryEngine.sql_query()."""
    return _get_engine().sql_query(schema, sql, limit)