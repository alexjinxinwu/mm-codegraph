## ADDED Requirements

### Requirement: codegraph-mcp is a thin stdio adapter

`codegraph-mcp` MUST contain only transport-specific code: stdio adapter, MCP protocol parsing, and response formatting. All business logic MUST delegate to `QueryEngine` in `codegraph-core`.

#### Scenario: MCP server delegates query execution to core
- **WHEN** an MCP request arrives via stdio
- **THEN** the MCP server parses the protocol, calls `QueryEngine` in `codegraph-core`, and formats the response — it performs no query logic itself

#### Scenario: MCP server has no business logic
- **WHEN** the codebase is examined for query primitives
- **THEN** `get_pool`, `q`, `_schema`, `out` implementations are found only in `codegraph-core`, not in `codegraph-mcp`

---

### Requirement: codegraph-mcp depends only on codegraph-core for query logic

`codegraph-mcp` MUST NOT contain any query engine, pool management, or schema validation code. It MUST import `QueryEngine` from `codegraph-core` and use it for all graph traversal operations.

#### Scenario: MCP module has no duplicate query logic
- **WHEN** static analysis is performed on `codegraph-mcp`
- **THEN** no implementations of `get_pool`, `q`, `_schema`, or `out` are found — only delegation to core

#### Scenario: MCP module imports QueryEngine from core
- **WHEN** the MCP server handles a request
- **THEN** it calls `QueryEngine` from `codegraph-core`, not a local copy