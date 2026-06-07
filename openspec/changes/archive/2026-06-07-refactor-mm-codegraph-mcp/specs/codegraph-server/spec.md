## ADDED Requirements

### Requirement: codegraph-server is a Python web application

`codegraph-server` MUST be a Python application (FastAPI or Flask) that exposes HTTP endpoints for graph browsing and analysis. It MUST depend on `codegraph-core` for all query and analysis logic.

#### Scenario: Server depends on codegraph-core
- **WHEN** `codegraph-server` starts
- **THEN** it imports `QueryEngine` from `codegraph-core` and uses it for all graph queries

#### Scenario: Server reuses analyzer_compat.py from core
- **WHEN** `codegraph-server` performs analysis
- **THEN** it imports and uses `analyzer_compat.py` from `codegraph-core`

---

### Requirement: codegraph-server exposes REST API for graph traversal

`codegraph-server` MUST expose HTTP endpoints that map to `QueryEngine` primitives (`get_pool`, `q`, `_schema`, `out`). The behavior of these endpoints MUST be identical to calling the corresponding methods on `QueryEngine` directly.

#### Scenario: HTTP endpoint calls QueryEngine with same behavior as MCP
- **WHEN** an HTTP client calls the query endpoint
- **THEN** `QueryEngine.q()` is invoked and returns results with the same semantics as when called from MCP stdio

#### Scenario: Server and MCP produce identical query results
- **WHEN** the same query is submitted via MCP stdio and via HTTP endpoint
- **THEN** the results are identical in structure and content, with zero behavioral difference