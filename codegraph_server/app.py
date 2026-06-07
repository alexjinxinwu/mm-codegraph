"""FastAPI application for codegraph-server."""

import sys
from pathlib import Path

# 允许在 codegraph_server 目录内直接 `python app.py`
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from codegraph_core.env_config import load_mysql_env

load_mysql_env(_REPO_ROOT)

from fastapi import FastAPI
from codegraph_server.routes import router

app = FastAPI(
    title="codegraph-server",
    description="HTTP API for code graph browsing and analysis",
    version="1.0.0",
)

app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)