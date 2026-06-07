## Context

The mm-codegraph MCP project currently has query primitives (`get_pool`, `q`, `_schema`, `out`) hardcoded into the MCP server process using stdio transport. This prevents reuse by a future HTTP API — any new web interface would need to reimplement the same logic, leading to behavioral drift.

The codebase currently lives in a single module. The refactor goal is to split into three modules:
- `codegraph-core`: everything broadly reusable (including `analyzer_compat.py`)
- `codegraph-mcp`: MCP-specific — stdio transport adapter, MCP protocol handling
- `codegraph-server`: HTTP web app, depends on core, reuses `analyzer_compat.py` and all other core logic

## Goals / Non-Goals

**Goals:**
- Extract `analyzer_compat.py` into `codegraph-core` so HTTP server can reuse it
- Keep MCP-specific code (stdio transport, protocol parsing) in `codegraph-mcp`
- Ensure everything not MCP-specific lives in core and is reusable by both MCP and server
- Unify connection pool, query execution, and schema validation across both transports

**Non-Goals:**
- This design does not specify the HTTP server framework or web UI details — that's a future change
- MCP transport adapter stays in `codegraph-mcp`; we are NOT making MCP depend on server
- Persistence layer (SQLite indexing) architecture is out of scope

## Decisions

### 1. Three-module structure: `codegraph-core`, `codegraph-mcp`, `codegraph-server`

```
codegraph-core/       — Shared Python logic: analyzer_compat.py, query engine (get_pool, q, _schema, out), data models, utilities
codegraph-mcp/        — MCP server: stdio transport adapter, MCP protocol parsing, depends on core
codegraph-server/     — Python HTTP web app: FastAPI/Flask REST API + web UI, depends on core, reuses analyzer_compat.py and query engine
```

**Rationale**: `analyzer_compat.py` belongs in core because the HTTP server needs it. MCP-specific transport code stays in `codegraph-mcp`. Everything else — query engine, `analyzer_compat.py`, data models — goes to `codegraph-core` for maximum reuse.

### 2. Query primitives (`get_pool`, `q`, `_schema`, `out`) live in core's `QueryEngine`

The MCP server delegates to `QueryEngine` in core. The HTTP server also calls `QueryEngine` directly. Both get identical behavior.

**Rationale**: Single source of truth for query semantics — no duplication, no drift.

### 3. `analyzer_compat.py` lives in `codegraph-core`

`analyzer_compat.py` is a shared utility that both MCP server and future HTTP server need — it goes into core, not MCP.

**Rationale**: Avoids duplicating compatibility logic. MCP server imports it from core; server imports it from core.

### 4. `codegraph-mcp` contains only MCP-specific code

MCP module = stdio transport + MCP protocol parsing + response formatting. It imports `QueryEngine` from core and wraps it for stdio.

**Rationale**: MCP is a transport adapter, not a logic container. All business logic is in core.

### 5. `codegraph-server` depends on core and reuses everything

The HTTP server uses core's `QueryEngine` for graph traversal and `analyzer_compat.py` for analysis. It adds only HTTP-specific layers (controllers, routing, web UI).

**Rationale**: Server is a client of core, same as MCP. Reusing `analyzer_compat.py` was the primary motivation for this refactor.

## Risks / Trade-offs

[Risk] `analyzer_compat.py` has MCP-specific assumptions → Mitigation: Audit `analyzer_compat.py` for MCP dependencies during move; extract any MCP-specific parts before moving.

[Risk] All modules are Python, so MCP and server must run in compatible Python environments → Mitigation: Use virtualenv or containerization to manage dependencies. Keep core's Python version aligned with MCP's requirements.

[Risk] Core becomes a dumping ground for unrelated utilities → Mitigation: Strict rule — only code that both MCP and server need goes in core. MCP-only goes to `codegraph-mcp`. Server-only goes to `codegraph-server`.

## Migration Plan

1. **Create `codegraph-core`** — move `analyzer_compat.py` here; move `QueryEngine`, `PoolManager`, `SchemaValidator` here; move data models here
2. **Create `codegraph-mcp`** — extract MCP-specific code (stdio transport, protocol parsing) from current single-module; depends on core
3. **Refactor current MCP server** → `codegraph-mcp` + `codegraph-core`
4. **Create `codegraph-server`** stub — depends on core; initially just a skeleton
5. **Verify** MCP server still works (regression: `analyzer_compat.py` behavior, query behavior unchanged)
6. **Build HTTP adapter** in server to confirm core reuse works for both `analyzer_compat.py` and query engine

**Rollback**: Revert to single-module structure if module boundaries prove too invasive.

## Open Questions

1. Which Python web framework for server — FastAPI or Flask? This affects routing and async patterns.
2. Should `analyzer_compat.py` be renamed to something more descriptive after moving to core?
3. Does `QueryEngine` in core need to be async to support concurrent HTTP requests?