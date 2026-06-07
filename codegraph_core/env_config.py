"""Load MySQL env vars from .mcp.json when not set in the process environment."""

import json
import os
from pathlib import Path

_MYSQL_KEYS = (
    "MMCG_MYSQL_HOST",
    "MMCG_MYSQL_PORT",
    "MMCG_MYSQL_USER",
    "MMCG_MYSQL_PASSWORD",
    "MMCG_MYSQL_POOL_SIZE",
)


def load_mysql_env(repo_root: Path | None = None) -> None:
    """Populate MMCG_MYSQL_* env vars from repo-root .mcp.json if MMCG_MYSQL_HOST is unset."""
    if os.environ.get("MMCG_MYSQL_HOST"):
        return

    root = repo_root or Path(__file__).resolve().parent.parent
    mcp_json = root / ".mcp.json"
    if not mcp_json.is_file():
        return

    with mcp_json.open(encoding="utf-8") as f:
        data = json.load(f)

    for server in data.get("mcpServers", {}).values():
        env = server.get("env") or {}
        for key in _MYSQL_KEYS:
            if key in env:
                os.environ.setdefault(key, str(env[key]))
        return
