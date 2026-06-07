## Why

Query primitives (`get_pool`, `q`, `_schema`, `out`) are currently hardcoded inside the MCP server process using stdio transport. A future HTTP API would need to reimplement the same logic, causing behavioral drift between the two interfaces. By extracting the query kernel into a shared module, both MCP (stdio) and future HTTP API will use identical connection pools, query execution, and schema validation — guaranteeing zero behavioral difference in graph traversal.

## What Changes

**Module restructuring** — single monolithic module splits into three:

- From: One module containing MCP server, query logic, and `analyzer_compat.py` all together
- To: `codegraph-core` (shared query engine + utilities), `codegraph-mcp` (MCP stdio adapter), `codegraph-server` (HTTP web app skeleton)
- Reason: Enable reuse of `analyzer_compat.py` and query engine by both MCP and future HTTP
- Impact: Non-breaking refactor — all existing MCP behavior preserved; HTTP server is net-new

**Query engine extraction** — `get_pool`, `q`, `_schema`, `out` primitives move from MCP process into `codegraph-core` as `QueryEngine` service interface. MCP server becomes a thin stdio adapter around it.

**`analyzer_compat.py` relocation** — from current location into `codegraph-core`. Both MCP and HTTP server will import it from core.

## Capabilities

### New Capabilities

- `query-engine`: Shared `QueryEngine` interface in `codegraph-core` implementing `get_pool`, `q`, `_schema`, `out` primitives. Both MCP stdio adapter and HTTP server call this interface — behavior is identical regardless of transport.
- `analyzer-compat`: `analyzer_compat.py` relocated to `codegraph-core`, reusable by both `codegraph-mcp` and `codegraph-server`.
- `codegraph-mcp`: New module containing MCP-specific transport code (stdio adapter, protocol parsing). Depends on `codegraph-core`. Acts as stdio client of the shared query engine.
- `codegraph-server`: New module containing HTTP web app skeleton. Depends on `codegraph-core`. Will expose REST API and web UI for graph browsing and analysis (details in future change).

### Modified Capabilities

- (none — this is a refactor, no existing spec requirements change)

## Impact

- **Code**: Query primitives and `analyzer_compat.py` move from current module to `codegraph-core`. MCP-specific transport code moves to `codegraph-mcp`.
- **APIs**: MCP server stdio interface unchanged (existing clients work without modification). HTTP API is future work, not part of this change.
- **Dependencies**: `codegraph-mcp` depends on `codegraph-core`. `codegraph-server` depends on `codegraph-core`.
- **Systems**: None — all changes are internal refactoring. MCP server behavior must remain identical after refactor.