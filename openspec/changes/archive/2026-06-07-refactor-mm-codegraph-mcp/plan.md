# codegraph-modularize Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development
> to implement this plan task-by-task.

**Goal:** Split the mm-codegraph codebase into three modules (core, mcp, server) so query primitives and `analyzer_compat.py` are reusable by both MCP stdio and HTTP transports.

**Architecture:** Python multi-package project with three modules. `codegraph-core` holds shared query engine and utilities. `codegraph-mcp` is the stdio transport adapter. `codegraph-server` is the Python HTTP web app (FastAPI/Flask).

**Tech Stack:** Python 3, SQLite, FastAPI or Flask, stdio transport (MCP protocol)

---

## Task 1: Create codegraph-core module structure

- [ ] **Step 1:** Create `codegraph-core/` directory with `__init__.py`, making it a Python package
- [ ] **Step 2:** Create `codegraph_core/query_engine.py` with `QueryEngine` class: `get_pool()`, `q()`, `_schema()`, `out()` methods
- [ ] **Step 3:** Create `codegraph_core/pool_manager.py` with `PoolManager` class: SQLite connection pool, lazy init, shared across transports
- [ ] **Step 4:** Create `codegraph_core/schema_validator.py` with `SchemaValidator` class: centralized schema validation before query execution
- [ ] **Step 5:** Create `codegraph_core/models.py` with data models (Symbol, Edge, FileNode)
- [ ] **Step 6:** Commit: "Add codegraph-core module structure"

---

## Task 2: Move analyzer_compat.py to codegraph-core

- [ ] **Step 1:** Audit current `analyzer_compat.py` for MCP-specific imports/dependencies
- [ ] **Step 2:** Extract any MCP-specific logic into a separate module under `codegraph-mcp`
- [ ] **Step 3:** Copy `analyzer_compat.py` into `codegraph-core/`
- [ ] **Step 4:** Add `__init__.py` to `codegraph-core/` to expose `analyzer_compat`
- [ ] **Step 5:** Verify `import codegraph_core.analyzer_compat` works from both MCP and server contexts
- [ ] **Step 6:** Commit: "Move analyzer_compat.py to codegraph-core"

---

## Task 3: Create codegraph-mcp module

- [ ] **Step 1:** Create `codegraph-mcp/` directory with `__init__.py`
- [ ] **Step 2:** Extract stdio transport adapter from current MCP server into `codegraph_mcp/stdio_adapter.py`
- [ ] **Step 3:** Extract MCP protocol parsing into `codegraph_mcp/protocol.py`
- [ ] **Step 4:** Create `codegraph_mcp/server.py` that imports `QueryEngine` from `codegraph-core` and delegates all query calls to it
- [ ] **Step 5:** Confirm no query logic remains in `codegraph-mcp` (only delegation and transport)
- [ ] **Step 6:** Run existing MCP tests — verify query behavior unchanged
- [ ] **Step 7:** Commit: "Create codegraph-mcp module with thin stdio adapter"

---

## Task 4: Create codegraph-server module

- [ ] **Step 1:** Create `codegraph-server/` directory with `__init__.py`
- [ ] **Step 2:** Set up `pyproject.toml` or `setup.py` with FastAPI or Flask as HTTP dependency
- [ ] **Step 3:** Create HTTP endpoints in `codegraph_server/routes.py`: `GET /pool`, `POST /q`, `GET /schema`, `POST /out`
- [ ] **Step 4:** Import `QueryEngine` from `codegraph-core` in server routes
- [ ] **Step 5:** Import `analyzer_compat` from `codegraph-core` in server analysis functions
- [ ] **Step 6:** Verify server starts and imports succeed
- [ ] **Step 7:** Commit: "Add codegraph-server module with HTTP endpoints"

---

## Task 5: Verification

- [ ] **Step 1:** Run existing MCP tests to confirm query behavior unchanged
- [ ] **Step 2:** Verify `analyzer_compat.py` imports without errors from both `codegraph-mcp` and `codegraph-server`
- [ ] **Step 3:** Confirm no duplicate query logic exists in `codegraph-mcp` (grep for `get_pool`, `q`, `_schema`, `out` implementations — only find in `codegraph-core`)
- [ ] **Step 4:** Commit: "Verify modularization — MCP regression tests pass"