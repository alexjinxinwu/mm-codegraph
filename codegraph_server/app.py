"""FastAPI application for codegraph-server."""

from fastapi import FastAPI
from .routes import router

app = FastAPI(
    title="codegraph-server",
    description="HTTP API for code graph browsing and analysis",
    version="1.0.0",
)

app.include_router(router)