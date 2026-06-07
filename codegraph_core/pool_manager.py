"""PoolManager — SQLite connection pool management (shared across transports)."""

import os
from typing import Optional

import pymysql
from dbutils.pooled_db import PooledDB


class PoolManager:
    """Manages the MySQL connection pool.

    Lives in codegraph-core so both MCP server process and HTTP server
    process obtain connections from the same pool instance.

    Uses lazy initialization — pool is created on first use.
    """

    _instance: Optional["PoolManager"] = None
    _pool: Optional[PooledDB] = None

    @classmethod
    def get_instance(cls) -> "PoolManager":
        """Return the singleton PoolManager instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_pool(self) -> PooledDB:
        """Return the pooled DB connection. Created lazily on first call."""
        if self._pool is None:
            self._pool = PooledDB(
                creator=pymysql,
                maxconnections=int(os.environ.get("MYSQL_POOL_SIZE", "5")),
                host=os.environ.get("MYSQL_HOST", "localhost"),
                port=int(os.environ.get("MYSQL_PORT", "3306")),
                user=os.environ.get("MYSQL_USER", "root"),
                password=os.environ.get("MYSQL_PASSWORD", "root"),
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                ping=1,
            )
        return self._pool

    def reset(self):
        """Clear the pool (useful for testing or reconfiguration)."""
        self._pool = None